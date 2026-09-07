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
prev, seek, volume. Needs `python-mutagen` installed
(`sudo pacman -S python-mutagen`) -- confirmed live that `addyt`'s own
post-processing step fails without it, surfaced here as a clear error
notification (not a silent no-op) if it's still missing.

Which exact queue entry gets played is *not* assumed from `addyt`'s own
exit code -- a real, directly-reported bug (an already-downloaded song
kept starting instead of the newly picked one) was root-caused with the
logging added here: `rmpc addyt` exits 0 even when the underlying
download genuinely fails (confirmed directly in the log -- a missing
python-mutagen produced a real error on stderr, but exit code 0), so an
earlier `if add.returncode != 0: return` check never fired, and
`rmpc play 0` ran unconditionally and played whatever was already
sitting at position 0. play_music() instead snapshots the real queue
before and after addyt and trusts *that* diff -- if the number of
entries in the queue didn't actually grow by exactly one, nothing gets
played and the real stderr is surfaced instead, regardless of what
addyt's own exit code claims.

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

Every run is logged to LOG_PATH (rotated at 1MB, 3 backups kept) --
the query, every subprocess command actually run and its exit code,
full stdout/stderr on failure, the queue snapshots for music mode, and
any unhandled exception with its full traceback. notify-send popups
stay the fast, at-a-glance feedback; the log is what to check afterward
when something's wrong and the popup's already gone.
"""
import concurrent.futures
import html
import json
import logging
import logging.handlers
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import urllib.request

STATE_DIR = os.path.expanduser("~/.local/state/music-search")
LOG_PATH = os.path.join(STATE_DIR, "music-search.log")

# Absolute paths, not theme names -- same reasoning as every other icon
# fix this session: mako has no GTK-style theme resolution, and these
# are Papirus's real-fill `status` icons, confirmed present before use.
ICON_INFO = "/usr/share/icons/Papirus/48x48/status/dialog-information.svg"
ICON_ERROR = "/usr/share/icons/Papirus/48x48/status/dialog-error.svg"
ICON_WARNING = "/usr/share/icons/Papirus/48x48/status/dialog-warning.svg"

VIDEO_FORMAT = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"


def setup_logging():
    os.makedirs(STATE_DIR, exist_ok=True)
    logger = logging.getLogger("music-search")
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


log = setup_logging()


def notify(title, body, icon=ICON_INFO, urgency="normal"):
    subprocess.run(
        ["notify-send", "-u", urgency, "-i", icon, title, body], check=False
    )


_LOG_TRUNCATE = 1000


def _truncated(text):
    if len(text) <= _LOG_TRUNCATE:
        return text
    return f"{text[:_LOG_TRUNCATE]}... [{len(text) - _LOG_TRUNCATE} more chars truncated]"


def run_logged(cmd, **kwargs):
    """subprocess.run wrapper that logs the exact command and its exit
    code/output every time -- the single choke point every external
    command in this script goes through, so nothing runs unlogged.
    Output is truncated in the log (not in what the function returns --
    callers still get the real, full stdout/stderr) -- yt-dlp's search
    output alone is tens of KB of JSON per call, and logging that in
    full on every single search would blow through the log's rotation
    size in a handful of runs, pushing out the far more useful entries
    (which are always short: a query, a video id, an error line) long
    before they'd naturally age out."""
    log.info("running: %s", " ".join(cmd))
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    proc = subprocess.run(cmd, **kwargs)
    level = logging.INFO if proc.returncode == 0 else logging.ERROR
    log.log(
        level, "exit=%s stdout=%r stderr=%r",
        proc.returncode, _truncated(proc.stdout or ""), _truncated(proc.stderr or ""),
    )
    return proc


def get_query(prompt):
    proc = run_logged(["wofi", "--show", "dmenu", "--prompt", prompt, "--lines", "1"])
    return proc.stdout.strip()


def search(query, count=10):
    """Search-only, via yt-dlp directly -- no Invidious. --flat-playlist
    keeps this fast (~2-3s for 10 results) since it only reads the
    search-results page itself, not each video's own full metadata."""
    proc = run_logged(
        ["yt-dlp", f"ytsearch{count}:{query}", "--flat-playlist", "--dump-json", "--no-warnings"],
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
    log.info("search %r -> %d result(s)", query, len(results))
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

        proc = run_logged(
            [
                "wofi", "--dmenu", "--allow-images", "--allow-markup", "--insensitive",
                "--matching", "fuzzy", "--prompt", "Pick a track...", "--lines", "10",
            ],
            input="\n".join(lines),
        )
        sel = proc.stdout.strip()
        picked = lookup.get(sel)
        log.info("picked: %s", picked.get("id") if picked else None)
        return picked
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
    cmd = ["mpv", "--no-terminal", "--force-window=yes", f"--ytdl-format={VIDEO_FORMAT}", url]
    log.info("launching (detached): %s", " ".join(cmd))
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def _queue_files():
    """{file: pos} for every entry currently in MPD's queue, via rmpc's
    own `queue` command -- used to snapshot before/after an addyt call
    so the actual new entry can be identified from real data instead of
    assumed from position-number bookkeeping."""
    proc = run_logged(["rmpc", "queue"], timeout=10)
    if proc.returncode != 0:
        return {}
    try:
        entries = json.loads(proc.stdout)
    except json.JSONDecodeError:
        log.error("couldn't parse `rmpc queue` output as JSON")
        return {}
    return {e["file"]: e.get("metadata", {}).get("pos") for e in entries}


def play_music(video_id, title):
    """Queues the picked video into MPD via rmpc's own `addyt` (rmpc
    already ships this -- yt-dlp under the hood, cached to
    ~/.cache/rmpc/youtube/ -- no reason to hand-roll a second download
    path), plays it, and opens rmpc so it's immediately visible with
    every normal rmpc/MPD control available: play, pause, next, prev,
    seek, volume.

    Does not trust that addyt's insert position and play's position
    argument necessarily agree with each other -- snapshots the queue
    before and after addyt, diffs them for the file that's actually new,
    and plays that file's own real `pos` from the AFTER snapshot. This
    is the direct fix for a real, reported bug: an already-downloaded
    song kept starting instead of the newly picked one, which is exactly
    what happens if a position assumption is wrong and `play <n>` lands
    on whatever was already sitting at that index.
    """
    url = f"https://youtube.com/watch?v={video_id}"
    notify("YouTube music", f"Adding to queue: {title}", icon=ICON_INFO)

    before = _queue_files()
    log.info("queue before addyt: %s", before)

    # addyt's own exit code is NOT trusted as the success/failure signal
    # -- confirmed directly, by logging it: a download that failed
    # (missing python-mutagen) still exited 0, with the real error only
    # visible in its stderr text. This is exactly how a real, reported
    # bug got past an earlier version of this function that checked
    # `if add.returncode != 0: return` -- that check never fired, so
    # `rmpc play 0` ran unconditionally and played whatever was already
    # sitting at position 0 (an older, already-downloaded song), not the
    # new one that had actually failed to download. The before/after
    # queue diff below is the only signal this function trusts now.
    add = run_logged(["rmpc", "addyt", "--position", "0", url], timeout=60)

    after = _queue_files()
    log.info("queue after addyt: %s", after)

    new_files = [f for f in after if f not in before]
    if len(new_files) != 1:
        # Covers both the confirmed real failure mode (0 new entries,
        # exit code lied) and a genuinely ambiguous result (2+ new
        # entries) -- neither is safe to guess a position for. Full
        # before/after state is already in the log above either way.
        err = add.stderr.strip().splitlines()[-1] if add.stderr.strip() else "unknown error"
        log.error("addyt did not produce exactly 1 new queue entry (found %d): %s", len(new_files), err)
        notify("YouTube music failed", err[:200], icon=ICON_ERROR, urgency="critical")
        return

    pos = after[new_files[0]]
    log.info("new entry %r is at real pos=%r -- playing that", new_files[0], pos)
    run_logged(["rmpc", "play", str(pos)], timeout=10)

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
    log.info("=== invoked with argv=%s ===", sys.argv[1:])

    if len(sys.argv) != 2 or sys.argv[1] not in ("video", "music"):
        print("usage: music-search.py video|music", file=sys.stderr)
        return 1
    mode = sys.argv[1]

    query = get_query(f"Search YouTube ({mode})...")
    if not query:
        log.info("empty query, exiting")
        return

    # Fired immediately after Enter -- confirmed live that without
    # this, wofi's query window just closes and nothing visible happens
    # for the ~2-3s the search itself takes, reading as "did my
    # keypress even register?" rather than "it's working".
    notify("YouTube search", f"Searching for \"{query}\"...", icon=ICON_INFO)

    try:
        results = search(query)
    except subprocess.TimeoutExpired:
        log.error("search timed out for query=%r", query)
        notify("YouTube search", "Search timed out", icon=ICON_WARNING, urgency="critical")
        return

    if not results:
        notify("YouTube search", f"No results for \"{query}\"", icon=ICON_WARNING)
        return

    picked = pick_result(results)
    if not picked:
        log.info("no result picked, exiting")
        return

    title = (picked.get("title") or "?").replace("\n", " ")
    video_id = picked.get("id")
    if not video_id:
        log.error("picked result had no video id: %r", picked)
        notify("YouTube search", "Couldn't get a video id for that result", icon=ICON_ERROR, urgency="critical")
        return

    if mode == "video":
        play_video(video_id, title)
    else:
        play_music(video_id, title)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # An unhandled exception here would otherwise just vanish --
        # this script is launched from a sway keybinding via wofi, with
        # nowhere any traceback on stderr would ever actually be seen.
        log.error("unhandled exception:\n%s", traceback.format_exc())
        notify("YouTube search", "Something went wrong -- see music-search.log", icon=ICON_ERROR, urgency="critical")
        sys.exit(1)
