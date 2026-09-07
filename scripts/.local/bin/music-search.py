#!/usr/bin/env python3
"""Search YouTube and immediately play the picked result -- as a real,
controllable video window (mpv) or straight into MPD's own queue via
rmpc (music), no Invidious involved.

Originally built to replace termusic's own `s` (youtube_search) popup,
which turned out to be entirely dependent on the public Invidious
instance network -- confirmed dead across the board (checked the live
instance directory directly: 0 of 11 currently-listed public instances
have their API enabled at all). termusic itself has since been replaced
entirely (rmpc + MPD now, see docs/ARCHITECTURE.md).

Usage: music-search.py video|music -- required, no default. Two direct
keybindings (Mod+Shift+Y / Mod+Ctrl+Shift+Y) instead of one key plus a
persisted mode toggle -- simpler to hold in your head, and there's
never a "which mode is it in right now" question to answer first.

**video** mode: mpv, a real floating window (sway/config's for_window
rule also explicitly focuses it -- confirmed live that a window
spawned this way doesn't get keyboard focus automatically, which
otherwise means every mpv keybind -- space, arrows, everything --
silently does nothing). Capped at 1080p
(`bestvideo[height<=1080]+bestaudio/best[height<=1080]`): confirmed
directly that yt-dlp's own "best" format picks whatever the highest
resolution available is (4K here) with zero regard for whether this
machine can decode it smoothly (dropped-frame count climbed
continuously in a live test) -- `height<=1080` picks the best format
that still satisfies the cap, so a video that only has 720p or lower
available correctly still gets its own actual highest tier, nothing is
ever force-upscaled or left unplayable.

**music** mode: does *not* download or launch anything of its own --
hands the picked URL straight to `rmpc addyt` (rmpc's own built-in
YouTube-to-queue command, already using yt-dlp under the hood, cached
to ~/.cache/rmpc/youtube/) and opens rmpc so it's immediately visible
and controllable with every normal rmpc/MPD action: play, pause, next,
prev, seek, volume. This replaced an earlier version of this script
that downloaded an mp3 into ~/Music directly and played it with a
headless, windowless mpv process -- which played real audio but had
*no way to stop, skip, or otherwise control it* once started, a real,
directly-reported problem, not a hypothetical one. rmpc already solves
this exact problem for its own library; there was no reason to solve
it worse a second time. Needs `python-mutagen` installed
(`sudo pacman -S python-mutagen`) -- confirmed live that `addyt`'s own
post-processing step fails without it, surfaced here as a clear error
notification (not a silent no-op) if it's still missing.

Flow: wofi prompt for a query (a "Searching..." notification fires
immediately after Enter -- confirmed live that without this, wofi's
query window just closes and nothing visible happens for the ~2-3s the
search itself takes, which reads as "did my keypress even register?")
-> yt-dlp search (--flat-playlist so it only fetches search-result-page
metadata, not per-video detail) -> wofi list of results (title,
uploader, duration -- duration shown specifically because search
results can include multi-hour livestreams alongside actual songs,
confirmed by literally picking one by accident once while testing
this) -> play (video) or queue+open rmpc (music).
"""
import concurrent.futures
import html
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request

# Absolute paths, not theme names -- same reasoning as every other icon
# fix this session: mako has no GTK-style theme resolution, and these
# are Papirus's real-fill `status` icons, confirmed present before use.
ICON_INFO = "/usr/share/icons/Papirus/48x48/status/dialog-information.svg"
ICON_ERROR = "/usr/share/icons/Papirus/48x48/status/dialog-error.svg"
ICON_WARNING = "/usr/share/icons/Papirus/48x48/status/dialog-warning.svg"

VIDEO_FORMAT = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"


def notify(title, body, icon=ICON_INFO, urgency="normal"):
    subprocess.run(
        ["notify-send", "-u", urgency, "-i", icon, title, body], check=False
    )


def get_query(prompt):
    result = subprocess.run(
        ["wofi", "--show", "dmenu", "--prompt", prompt, "--lines", "1"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def search(query, count=10):
    """Search-only, via yt-dlp directly -- no Invidious. --flat-playlist
    keeps this fast (~2-3s for 10 results) since it only reads the
    search-results page itself, not each video's own full metadata."""
    proc = subprocess.run(
        [
            "yt-dlp",
            f"ytsearch{count}:{query}",
            "--flat-playlist",
            "--dump-json",
            "--no-warnings",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    results = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        results.append(d)
    return results


def format_duration(seconds):
    if not seconds:
        return "?:??"
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def fetch_thumbnail(video_id, dest_dir):
    """YouTube's `hqdefault.jpg` is a fixed, unsigned URL shape (no
    per-request query-string tokens the way the URLs in yt-dlp's own
    `thumbnails` JSON array have) -- confirmed directly it resolves
    (200, ~21KB, a real 480x360 jpeg) without needing to parse or pick
    from that array at all. Was `mqdefault.jpg` (320x180, ~11-18KB)
    originally -- switched after direct feedback that results looked
    pixelated: confirmed live that `hqdefault` is reliably available
    at the same fixed URL shape (curl'd it directly, not assumed from
    YouTube's naming convention) and is meaningfully less compressed
    (~2x the bytes for the same subject), even though wofi's own
    `image_size=32` (`wofi/.config/wofi/config`) downscales either
    tier the same amount -- more real source detail before that
    downscale still reduces the compression-artifact "pixelated" look
    a heavily-compressed 320x180 source has. Small enough that
    fetching all ~10 results concurrently is still fast (confirmed
    directly: ~0.4s for 10 at the smaller mqdefault size, ~0.5s for
    10 at this larger hqdefault size -- a real, small cost, not
    hand-waved as "still fast" without checking)."""
    path = f"{dest_dir}/{video_id}.jpg"
    try:
        with urllib.request.urlopen(
            f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg", timeout=5
        ) as r:
            with open(path, "wb") as f:
                f.write(r.read())
        return path
    except Exception:
        return None


def pick_result(results):
    # A row with just text ("only text doesn't make that much sense",
    # reported directly) doesn't actually tell you much about a video --
    # the thumbnail is what makes a search result recognizable at a
    # glance the way it would be on YouTube itself. wofi's own `img:`
    # dmenu markup (--allow-images, already used the same way in
    # notification-history.py) handles this directly; no need to build
    # anything bespoke.
    thumb_dir = tempfile.mkdtemp(prefix="music-search-thumbs-")
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            thumb_paths = list(
                ex.map(lambda d: fetch_thumbnail(d.get("id"), thumb_dir), results)
            )

        lines = []
        lookup = {}
        for d, thumb in zip(results, thumb_paths):
            title = (d.get("title") or "?").replace("\n", " ")
            uploader = d.get("uploader") or d.get("channel") or "?"
            dur = format_duration(d.get("duration"))
            text = f"<b>{html.escape(title)}</b>  --  {html.escape(uploader)}  ({dur})"
            prefix = f"img:{thumb}:text:" if thumb else "text:"
            line = f"{prefix}{text}"
            lines.append(line)
            lookup[line] = d

        proc = subprocess.run(
            [
                "wofi",
                "--dmenu",
                "--allow-images",
                "--allow-markup",
                "--insensitive",
                "--matching",
                "fuzzy",
                "--prompt",
                "Pick a track...",
                "--lines",
                "10",
            ],
            input="\n".join(lines),
            capture_output=True,
            text=True,
        )
        sel = proc.stdout.strip()
        return lookup.get(sel)
    finally:
        # Only needed for wofi to have something to read while the list
        # is open -- nothing downstream touches these, so they're safe
        # to clean up unconditionally afterward.
        shutil.rmtree(thumb_dir, ignore_errors=True)


def play_video(video_id, title):
    """Launches mpv detached (Popen, not run) and returns immediately --
    this script's job is "start playback", not "wait for the video to
    finish". toggle-popup.sh (sway/config's wrapper around this script)
    tracks "is the popup open" by whether this process is still alive;
    blocking here for the full video duration would keep that marker
    alive the whole time too, so this returns as soon as mpv has
    actually launched, letting toggle-popup.sh -- and Mod+Shift+Y
    itself -- behave normally again right away. Keyboard focus (so
    space/arrows/etc. actually reach the new window) is handled by
    sway/config's own for_window rule, not here.
    """
    url = f"https://youtube.com/watch?v={video_id}"
    notify("YouTube video", f"Playing: {title}", icon=ICON_INFO)
    subprocess.Popen(
        ["mpv", "--no-terminal", "--force-window=yes", f"--ytdl-format={VIDEO_FORMAT}", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def play_music(video_id, title):
    """Queues the picked video into MPD via rmpc's own `addyt` (rmpc
    already ships this -- yt-dlp under the hood, cached to
    ~/.cache/rmpc/youtube/ -- no reason to hand-roll a second download
    path) at the front of the queue, plays it, and opens rmpc so it's
    immediately visible with every normal rmpc/MPD control available:
    play, pause, next, prev, seek, volume. This is the fix for a real,
    directly-reported problem with the previous version of this
    script -- a headless mpv process playing real audio with no window,
    no indicator, and no way to stop it short of finding and killing
    the process by hand.
    """
    url = f"https://youtube.com/watch?v={video_id}"
    notify("YouTube music", f"Adding to queue: {title}", icon=ICON_INFO)

    add = subprocess.run(
        ["rmpc", "addyt", "--position", "0", url],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if add.returncode != 0:
        # Surfaced honestly rather than swallowed -- confirmed live this
        # is exactly how a missing python-mutagen (rmpc's own YouTube
        # feature dependency) shows up: addyt exits non-zero with a
        # real, specific error on stderr, not a generic failure.
        err = add.stderr.strip().splitlines()[-1] if add.stderr.strip() else "unknown error"
        notify("YouTube music failed", err[:200], icon=ICON_ERROR, urgency="critical")
        return

    subprocess.run(["rmpc", "play", "0"], capture_output=True, text=True, timeout=10, check=False)

    # Same launcher rmpc's own keybinding uses -- opens the window if
    # it doesn't exist yet, or brings it to front if rmpc is already
    # running, so the track that was just queued is immediately visible
    # and controllable, not just playing somewhere unseen.
    subprocess.Popen(
        ["/home/yash/.local/bin/rmpc-toggle.sh"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("video", "music"):
        print("usage: music-search.py video|music", file=sys.stderr)
        return 1
    mode = sys.argv[1]

    query = get_query(f"Search YouTube ({mode})...")
    if not query:
        return

    # Fired immediately after Enter -- confirmed live that without
    # this, wofi's query window just closes and nothing visible happens
    # for the ~2-3s the search itself takes, reading as "did my
    # keypress even register?" rather than "it's working".
    notify("YouTube search", f"Searching for \"{query}\"...", icon=ICON_INFO)

    try:
        results = search(query)
    except subprocess.TimeoutExpired:
        notify("YouTube search", "Search timed out", icon=ICON_WARNING, urgency="critical")
        return

    if not results:
        notify("YouTube search", f"No results for \"{query}\"", icon=ICON_WARNING)
        return

    picked = pick_result(results)
    if not picked:
        return

    title = (picked.get("title") or "?").replace("\n", " ")
    video_id = picked.get("id")
    if not video_id:
        notify("YouTube search", "Couldn't get a video id for that result", icon=ICON_ERROR, urgency="critical")
        return

    if mode == "video":
        play_video(video_id, title)
    else:
        play_music(video_id, title)


if __name__ == "__main__":
    sys.exit(main())
