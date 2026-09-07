#!/usr/bin/env python3
"""Search YouTube and either play the picked result immediately (mpv)
or download it into the local music library, no Invidious involved.

Originally built to replace termusic's own `s` (youtube_search) popup,
which turned out to be entirely dependent on the public Invidious
instance network -- confirmed dead across the board (checked the live
instance directory directly: 0 of 11 currently-listed public instances
have their API enabled at all). termusic itself has since been replaced
entirely (rmpc + MPD now, see docs/ARCHITECTURE.md).

Default action is now **play**, not download -- Mod+Shift+Y should get
you listening/watching immediately, not leave you waiting on a download
first. mpv handles this directly via its bundled yt-dlp hook (confirmed
live: `mpv <youtube-url>` resolves and plays with zero extra plumbing,
both `--no-video --ytdl-format=bestaudio` for audio-only and
`--force-window=yes` for real video, each verified end-to-end by reading
back mpv's own IPC `time-pos` as it advanced, not just checking the
process stayed alive). Whether Enter plays audio or video is controlled
by a persisted toggle (media-play-mode.sh, Mod+Ctrl+Y) -- read fresh
every run via read_play_mode() below, so switching modes takes effect on
the very next search with no restart of anything needed.

The original download-to-library behavior hasn't been removed, just
moved off the default path: `--download` (bound to Mod+Shift+Ctrl+Y)
reuses all the same search/pick code above and does exactly what this
script always did -- get a real mp3 with embedded art into ~/Music,
where MPD's own filesystem watcher (`auto_update "yes"`,
mpd/.config/mpd/mpd.conf) picks it up on its own, no restart or manual
rescan needed (confirmed directly by watching MPD's own log after
dropping a file into ~/Music with no client open at all).

Flow: wofi prompt for a query -> yt-dlp search (fast, ~2-3s, --flat-playlist
so it only fetches search-result-page metadata, not per-video detail) ->
wofi list of results (title, uploader, duration -- duration shown
specifically because search results can include multi-hour livestreams
alongside actual songs, confirmed by literally downloading one by
accident once while testing this) -> play (default) or download
(--download) the picked one.

`--extractor-args "youtube:player_client=android"` on the download step
specifically: confirmed directly, not assumed, that yt-dlp's default
web-client extraction hit YouTube's "Sign in to confirm you're not a
bot" wall on 2 of 3 real test downloads, while the exact same URLs
downloaded cleanly every time with this flag -- a known, standard
workaround (the android player API isn't gated behind the same
web-based verification), not something invented here. mpv's own ytdl
hook hit no such wall in direct testing, so the play path doesn't carry
this flag -- if that changes later, `--ytdl-raw-options` is the place to
add the equivalent for mpv.
"""
import concurrent.futures
import glob
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

MUSIC_DIR = os.path.expanduser("~/Music")
PLAY_MODE_FILE = os.path.expanduser("~/.local/state/media-play-mode/current")

# Absolute paths, not theme names -- same reasoning as every other icon
# fix this session: mako has no GTK-style theme resolution, and these
# are Papirus's real-fill `status` icons, confirmed present before use.
ICON_INFO = "/usr/share/icons/Papirus/48x48/status/dialog-information.svg"
ICON_ERROR = "/usr/share/icons/Papirus/48x48/status/dialog-error.svg"
ICON_WARNING = "/usr/share/icons/Papirus/48x48/status/dialog-warning.svg"


def notify(title, body, icon=ICON_INFO, urgency="normal"):
    subprocess.run(
        ["notify-send", "-u", urgency, "-i", icon, title, body], check=False
    )


def read_play_mode():
    """"audio" or "video", persisted by media-play-mode.sh (Mod+Ctrl+Y)
    -- read fresh on every run rather than cached anywhere, so toggling
    the mode always takes effect on the very next search."""
    try:
        mode = open(PLAY_MODE_FILE).read().strip()
    except OSError:
        mode = ""
    return mode if mode in ("audio", "video") else "audio"


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
    path = os.path.join(dest_dir, f"{video_id}.jpg")
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
        # is open -- nothing downstream (the download step) touches
        # these, so they're safe to clean up unconditionally afterward.
        shutil.rmtree(thumb_dir, ignore_errors=True)


def play(video_id, title, mode):
    """Launches mpv detached (Popen, not run) and returns immediately --
    this script's job is "start playback", not "wait for the song/video
    to finish". toggle-popup.sh (sway/config's wrapper around this
    script) tracks "is the popup open" by whether this process is still
    alive; blocking here for the full playback duration would keep that
    marker alive the whole time too, so this returns as soon as mpv has
    actually launched, letting toggle-popup.sh -- and Mod+Shift+Y itself
    -- behave normally again right away.

    Video is capped at 1080p (`height<=?1080`) rather than trusting
    mpv/yt-dlp's own "best" default -- confirmed directly that "best"
    picks whatever the highest available resolution is (4K here, for a
    result that had it) with zero regard for whether the machine can
    actually decode/display it smoothly at that size: dropped-frame
    count climbed continuously in a live 4K test versus this run
    cleanly. Audio-only mode uses --ytdl-format=bestaudio specifically
    (not just --no-video) so yt-dlp fetches only an audio stream over
    the network in the first place, not a full video+audio stream with
    the video half simply never rendered.
    """
    url = f"https://youtube.com/watch?v={video_id}"
    notify("Music search", f"Playing ({mode}): {title}", icon=ICON_INFO)

    cmd = ["mpv", "--no-terminal", f"--force-window={'yes' if mode == 'video' else 'no'}"]
    if mode == "audio":
        cmd += ["--no-video", "--ytdl-format=bestaudio"]
    else:
        cmd += ["--ytdl-format=bestvideo[height<=?1080]+bestaudio/best[height<=?1080]"]
    cmd.append(url)

    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def download(video_id, title):
    url = f"https://youtube.com/watch?v={video_id}"
    notify("Music search", f"Downloading: {title}", icon=ICON_INFO)

    proc = subprocess.run(
        [
            "yt-dlp",
            "-x",
            "--audio-format",
            "mp3",
            "--embed-thumbnail",
            "--add-metadata",
            "--write-thumbnail",
            # See module docstring -- confirmed directly this avoids the
            # "Sign in to confirm you're not a bot" wall the default web
            # client hits on a real fraction of videos.
            "--extractor-args",
            "youtube:player_client=android",
            "--no-warnings",
            "-o",
            os.path.join(MUSIC_DIR, "%(title)s.%(ext)s"),
            url,
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )

    if proc.returncode != 0:
        # Bot-check and other yt-dlp failures land here -- surfaced
        # honestly rather than silently swallowed, with enough of the
        # real error visible to actually act on (e.g. try a different
        # result if this one specifically is blocked).
        err = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "unknown error"
        notify("Music search failed", err[:200], icon=ICON_ERROR, urgency="critical")
        return

    # Use the track's own thumbnail as the completion notification's
    # icon -- same "the real fetched image is its own icon" pattern
    # fetch_wallpaper.sh already uses. Deliberately *not* reconstructing
    # the expected filename from `title` -- a real bug caught by testing
    # this directly: yt-dlp's own filesystem sanitization doesn't match
    # the raw title string (confirmed on a real download -- the search
    # JSON's title had a plain ASCII "|", the file yt-dlp actually wrote
    # had a fullwidth "｜" in its place, U+FF5C, since a literal pipe
    # isn't filesystem-safe), so a glob built from `title` silently
    # matched nothing and left the thumbnail undeleted. Finding the
    # newest image file in MUSIC_DIR instead sidesteps needing to
    # predict yt-dlp's own sanitization rules at all -- safe here since
    # this script only ever runs one download at a time.
    thumb_icon = ICON_INFO
    thumbs = sorted(
        (
            p
            for ext in ("jpg", "jpeg", "webp", "png")
            for p in glob.glob(os.path.join(MUSIC_DIR, f"*.{ext}"))
        ),
        key=os.path.getmtime,
        reverse=True,
    )
    if thumbs:
        thumb_icon = thumbs[0]
        thumbs = thumbs[:1]

    notify("Music search", f"Downloaded: {title}", icon=thumb_icon)

    # The separate thumbnail file's only purpose was this notification
    # icon -- the mp3 already has the same art embedded
    # (--embed-thumbnail above). Removing it afterward keeps ~/Music a
    # clean folder of just tracks for MPD's own library scan, instead
    # of a stray image file sitting next to every song.
    for t in thumbs:
        try:
            os.remove(t)
        except OSError:
            pass


def main():
    # --download (Mod+Shift+Ctrl+Y) is the only flag -- everything else
    # is the default, unconditional "play" action (Mod+Shift+Y).
    do_download = "--download" in sys.argv[1:]

    os.makedirs(MUSIC_DIR, exist_ok=True)

    if do_download:
        prompt = "Search YouTube (download)..."
    else:
        mode = read_play_mode()
        prompt = f"Search YouTube ({mode})..."

    query = get_query(prompt)
    if not query:
        return

    try:
        results = search(query)
    except subprocess.TimeoutExpired:
        notify("Music search", "Search timed out", icon=ICON_WARNING, urgency="critical")
        return

    if not results:
        notify("Music search", f"No results for \"{query}\"", icon=ICON_WARNING)
        return

    picked = pick_result(results)
    if not picked:
        return

    title = (picked.get("title") or "?").replace("\n", " ")
    video_id = picked.get("id")
    if not video_id:
        notify("Music search", "Couldn't get a video id for that result", icon=ICON_ERROR, urgency="critical")
        return

    if do_download:
        try:
            download(video_id, title)
        except subprocess.TimeoutExpired:
            notify("Music search", f"Download timed out: {title}", icon=ICON_ERROR, urgency="critical")
    else:
        play(video_id, title, read_play_mode())


if __name__ == "__main__":
    sys.exit(main())
