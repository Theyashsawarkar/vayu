#!/usr/bin/env python3
"""Bar events: refreshes waybar capsules, and tmux's docker count, when the
thing they show changes -- instead of each capsule polling on a timer.
Systemd user unit bar-events.service, started by sway after waybar.

  capsule     waybar signal   event
  bell        8               org.freedesktop.Notifications NotificationClosed
                              (the history grows when one closes), and
                              akashvani's dev.vayu.Akashvani Changed (modes:
                              do not disturb from the panel, a timer, a key)
  theme       11              GSettings color-scheme changed (dconf)
  jyoti     12              swayidle.service ActiveState (user systemd)
  ekatva      13              ekatva.service ActiveState (user systemd)
  docker      14              docker.service ActiveState (system systemd),
                              then `docker events` start/die while it runs
  hotspot     15              NetworkManager's ActiveConnections, and
                              `iw event` new/del station (a device joined
                              or left the hotspot)
  volume      17              `pactl subscribe`: the output itself changed
                              (a sink, a card, the server's default), not
                              each app's stream; waybar then runs
                              `bar-volume --once` (this used to be a
                              second interpreter, `bar-volume` streaming)

tmux's pull request capsule (@gh_reviews, @gh_prs) is set from gh-review-count every
2 minutes (GitHub has no push for "review requested" to a desktop), and
right away when the account it counts changes -- gh's hosts.yml (gh auth
switch), sangam's last-account (u in sangam) -- or sangam says PRs changed
(~/.cache/sangam/changed: a merge, review or reload there, or by an agent
through `sangam mcp`). Its unread mail and chat capsule (@narada_mail,
@narada_chat) follows narada's local copy (its database changes when a
sync brings mail or you read something), asking `narada status`; WhatsApp
gets its own green capsule (@narada_whatsapp). Its dev
servers capsule (@dev_ports) from dev-ports every 15 seconds (listening
sockets have no event). Its Claude limit capsule (@claude_limit, and
@claude_limit_class ok/warn/full) runs `vesha waybar --once` when one of
the files `vesha waybar --sources` names changes: the accounts (a switch,
at once) and the usage cache (at most once a minute, as the stream did). A
vesha without --sources (before v0.7.0) is followed through `vesha waybar`,
which prints a line whenever the account or its usage changes.

Caps Lock / Num Lock (9, 10) are signalled by sway's --release binds and
keylock-toggle.sh. Everything else on the bar is waybar-internal.

Each capsule's own script still builds its text; this only says "now".
Bursts (compose starts several containers) collapse into one refresh 0.3 s after
the last event.

`bar-events.py --tmux-docker` sets tmux's @docker_count once and exits
(tmux.conf runs it on load, since tmux can start after this daemon);
`--tmux-narada` the same for @narada_mail and @narada_chat, and
`--tmux-claude` for @claude_limit (`vesha waybar` only prints on a change,
so a tmux started after this daemon would otherwise never get it).
"""
import os
import re
import signal
import subprocess
import sys

from gi.repository import Gio, GLib

WAYBAR_SIGNAL = {"bell": 8, "theme": 11, "jyoti": 12, "ekatva": 13, "docker": 14, "hotspot": 15, "volume": 17}
# How long a capsule waits for a burst to end before refreshing (ms): a
# scroll on the sound capsule is a burst of volume steps, and the number
# should follow the wheel.
DELAY = {"volume": 50}
NM = "org.freedesktop.NetworkManager"
iw_events = None  # the running `iw event` Gio.Subprocess
SD = "org.freedesktop.systemd1"

pending = {}          # capsule -> GLib source id of its scheduled refresh
docker_active = False
docker_events = None  # the running `docker events` Gio.Subprocess


def log(*a):
    print("bar-events:", *a, file=sys.stderr, flush=True)


def tmux(*args):
    """Sets something on the default tmux server. With a timeout: these run
    on the main loop, and a stuck tmux server froze every capsule refresh."""
    try:
        r = subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=3)
        if r.returncode and "no server running" not in r.stderr:
            log("tmux", *args, "failed:", r.stderr.strip())
    except (OSError, subprocess.TimeoutExpired) as e:
        log("tmux", *args, "failed:", e)


def refresh(name):
    if name in pending:
        GLib.source_remove(pending[name])
    pending[name] = GLib.timeout_add(DELAY.get(name, 300), fire, name)


def fire(name):
    pending.pop(name, None)
    if name == "docker":
        tmux_docker()
    signal_waybar(WAYBAR_SIGNAL[name])
    return False


def signal_waybar(n):
    """Sends SIGRTMIN+n to waybar, but only to one that already catches it
    (SigCgt in /proc). An RT signal's default action is to terminate, so
    one sent while waybar is still starting kills the bar -- which this
    daemon's startup refresh did at login. A starting waybar runs every
    capsule script anyway. Same check as the waybar-signal script."""
    sig = signal.SIGRTMIN + n
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open(f"/proc/{pid}/status") as f:
                fields = dict(line.split(":", 1) for line in f if line.startswith(("Name:", "SigCgt:")))
            if fields.get("Name", "").strip() == "waybar" and int(fields["SigCgt"], 16) >> (sig - 1) & 1:
                os.kill(int(pid), sig)
        except (OSError, KeyError, ValueError):
            pass  # exited meanwhile, or not ours to read


def tmux_docker():
    """Sets @docker_count on the default tmux server (tmux.conf shows it).
    `docker ps` only while the daemon runs: it's socket-activated, and
    asking a stopped one would start it."""
    count = 0
    if docker_active:
        try:
            out = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=5)
            count = len(out.stdout.split())
        except (OSError, subprocess.TimeoutExpired) as e:
            log("docker ps failed:", e)
    tmux("set", "-g", "@docker_count", str(count))


def watch_unit(bus, unit, on_state):
    """Calls on_state(ActiveState) now and on every change of a systemd
    unit. Subscribe makes systemd send the changes at all; it's per
    connection, and systemd ignores a second Subscribe on the same one."""
    try:
        bus.call_sync(SD, "/org/freedesktop/systemd1", f"{SD}.Manager", "Subscribe",
                      None, None, Gio.DBusCallFlags.NONE, -1, None)
    except GLib.Error as e:
        if "already subscribed" not in e.message.lower():
            raise
    path = bus.call_sync(SD, "/org/freedesktop/systemd1", f"{SD}.Manager", "LoadUnit",
                         GLib.Variant("(s)", (unit,)), None, Gio.DBusCallFlags.NONE, -1,
                         None).unpack()[0]

    def changed(_conn, _sender, _path, _iface, _member, params):
        iface, props, _ = params.unpack()
        if iface == f"{SD}.Unit" and "ActiveState" in props:
            on_state(props["ActiveState"])

    bus.signal_subscribe(SD, "org.freedesktop.DBus.Properties", "PropertiesChanged", path,
                         None, Gio.DBusSignalFlags.NONE, changed)
    state = bus.call_sync(SD, path, "org.freedesktop.DBus.Properties", "Get",
                          GLib.Variant("(ss)", (f"{SD}.Unit", "ActiveState")), None,
                          Gio.DBusCallFlags.NONE, -1, None).unpack()[0]
    on_state(state)


def on_docker_state(state):
    global docker_active, docker_events
    if state not in ("active", "inactive", "failed"):
        return  # activating / deactivating: wait for where it lands
    docker_active = state == "active"
    if docker_active and docker_events is None:
        docker_events = Gio.Subprocess.new(
            ["docker", "events", "--filter", "type=container", "--filter", "event=start",
             "--filter", "event=die", "--format", "{{.Action}}"],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
        read_docker_events(Gio.DataInputStream.new(docker_events.get_stdout_pipe()), docker_events)
    elif not docker_active and docker_events is not None:
        docker_events.force_exit()
        docker_events = None
    refresh("docker")


def read_docker_events(stream, proc):
    def got_line(s, result):
        global docker_events
        try:
            line, _ = s.read_line_finish_utf8(result)
        except GLib.Error:
            line = None
        if line is None:  # `docker events` exited
            if docker_events is proc:
                docker_events = None
                if docker_active:   # but docker didn't stop: follow it again
                    log("docker events exited; restarting it in 5 s")
                    GLib.timeout_add_seconds(5, lambda: (docker_active and docker_events is None
                                                         and on_docker_state("active"), False)[1])
            return
        refresh("docker")
        s.read_line_async(GLib.PRIORITY_DEFAULT, None, got_line)

    stream.read_line_async(GLib.PRIORITY_DEFAULT, None, got_line)


busy = set()   # helpers still running from their last tick
again = set()  # helpers asked for while running: run once more when done


def run_once(name, *args, rerun=False):
    """Starts a helper in the background unless its last run is still going
    (a hung `gh api` used to pile up a new one every 5 minutes). With
    rerun, a call during a run starts one more after it instead of being
    dropped (the account changed: the running one counts the old one).
    Its stderr goes to this service's journal. Returns True to keep the
    GLib timer."""
    if name in busy:
        if rerun:
            again.add(name)
        else:
            log(f"{name}: last run still going, skipping this one")
        return True
    try:
        proc = Gio.Subprocess.new([os.path.expanduser(f"~/.local/bin/{name}"), *args],
                                  Gio.SubprocessFlags.STDOUT_SILENCE)
    except GLib.Error as e:
        log(f"{name}:", e.message)
        return True
    busy.add(name)

    def done(p, result):
        busy.discard(name)
        if name in again:
            again.discard(name)
            GLib.idle_add(lambda: (run_once(name, *args), False)[1])
        try:
            p.wait_finish(result)
            if p.get_if_exited() and p.get_exit_status():
                log(f"{name} exited with status {p.get_exit_status()}")
        except GLib.Error as e:
            log(f"{name}:", e.message)
    proc.wait_async(None, done)
    return True


def gh_reviews(rerun=False):
    """gh-review-count sets tmux's @gh_reviews, @gh_prs and @gh_account."""
    return run_once("gh-review-count", "--set-tmux", rerun=rerun)


gh_monitors = []  # kept alive: a dropped Gio.FileMonitor stops watching


def watch_gh_account():
    """Recounts as soon as the account the PR capsule counts changes, or
    sangam changed a PR, so the bar never lags behind sangam. Once more
    30 s later: GitHub's search index (what the count asks) lists a just
    merged PR as open for a few seconds. A file monitor also sees a file
    that doesn't exist yet appear (sangam never run) and gh's
    write-and-rename of hosts.yml."""
    config = os.environ.get("GH_CONFIG_DIR") or os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "gh")
    cache = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    for path in (os.path.join(config, "hosts.yml"), os.path.join(cache, "sangam", "last-account"),
                 os.path.join(cache, "sangam", "changed")):
        try:
            m = Gio.File.new_for_path(path).monitor_file(Gio.FileMonitorFlags.WATCH_MOVES, None)
        except GLib.Error as e:
            log(f"can't watch {path}, the PR capsule follows it every 2 minutes only:", e.message)
            continue
        m.set_rate_limit(1000)
        m.connect("changed", lambda *a: (debounce("gh-account", lambda: gh_reviews(rerun=True)),
                                         debounce("gh-settle", lambda: gh_reviews(rerun=True), 30000)))
        gh_monitors.append(m)


NARADA = os.path.expanduser("~/.local/bin/narada")
narada_monitor = None  # kept alive, like gh_monitors
narada_last = {}       # tmux option -> the count last set (skip unchanged)


def set_narada(out):
    """@narada_mail / @narada_chat / @narada_whatsapp from `narada
    status --json` output; unset (no capsule) when narada can't say, and
    the WhatsApp one when WhatsApp isn't linked (-1) or narada predates it."""
    import json
    try:
        d = json.loads(out or "")
        mail, chat = int(d.get("mail", 0)), int(d.get("chat", 0))
        wa = int(d.get("whatsapp", -1))
    except (ValueError, TypeError, AttributeError):
        for opt in ("@narada_mail", "@narada_chat", "@narada_whatsapp"):
            tmux("set", "-gu", opt)
        narada_last.clear()
        return
    # Only what changed: this runs every few seconds while WhatsApp syncs,
    # and three tmux processes each time were most of this unit's CPU.
    for opt, val in (("@narada_mail", mail), ("@narada_chat", chat), ("@narada_whatsapp", wa)):
        if narada_last.get(opt) == val:
            continue
        narada_last[opt] = val
        if val < 0:
            tmux("set", "-gu", opt)
        else:
            tmux("set", "-g", opt, str(val))


def tmux_narada():
    """Asks narada for its unread counts (its local copy, no network) in
    the background: SQLite can wait on a sync's write lock."""
    if not os.access(NARADA, os.X_OK):
        return False
    if "narada" in busy:
        again.add("narada")
        return False
    try:
        proc = Gio.Subprocess.new([NARADA, "status", "--json"],
                                  Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error as e:
        log("narada status:", e.message)
        return False
    busy.add("narada")

    def done(p, result):
        busy.discard("narada")
        try:
            _, out, _ = p.communicate_utf8_finish(result)
        except GLib.Error as e:
            log("narada status:", e.message)
            out = None
        if p.get_if_exited() and p.get_exit_status() == 0:
            set_narada(out)
        if "narada" in again:
            again.discard("narada")
            tmux_narada()
    proc.communicate_utf8_async(None, None, done)
    return False


NARADA_COUNTS = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"),
                             "narada", "counts.json")


def read_narada_counts(*_):
    """counts.json is exactly `narada status --json`, rewritten (by rename)
    only when a count changes: read it, no narada process, no SQLite."""
    try:
        with open(NARADA_COUNTS) as f:
            set_narada(f.read())
    except OSError:
        pass
    return False


def watch_narada():
    """narada's unread counts. A narada that writes counts.json (its daemon
    rewrites it only when a count changes) is watched there: one event per
    change. An older narada: its data folder, whose database (and WAL)
    change on every sync write, asking `narada status` each time (throttled)."""
    global narada_monitor
    if os.path.exists(NARADA_COUNTS):
        state = os.path.dirname(NARADA_COUNTS)
        try:
            narada_monitor = Gio.File.new_for_path(state).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
        except GLib.Error as e:
            log(f"can't watch {state}:", e.message)
        else:
            def changed(_m, f, other, _event):
                if NARADA_COUNTS in (f.get_path(), other.get_path() if other else None):
                    debounce("narada-counts", read_narada_counts, 200)
            narada_monitor.connect("changed", changed)
            read_narada_counts()
            return
    data = os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "narada")
    try:
        narada_monitor = Gio.File.new_for_path(data).monitor_directory(Gio.FileMonitorFlags.NONE, None)
    except GLib.Error as e:
        log(f"can't watch {data}, the mail capsule updates every 2 minutes only:", e.message)
        return
    narada_monitor.set_rate_limit(1000)
    # Throttled, not debounced: WhatsApp's sync writes about every second,
    # so a 1 s debounce fired every 1.4 s (8% of a core at idle) and a
    # longer one would never fire while it syncs. At most one check every
    # 3 s, and always one after the last change.
    narada_monitor.connect("changed", lambda *a: throttle("narada", tmux_narada, 3000))


def debounce(key, fn, ms=500):
    """Runs fn once, ms after the last call with this key (a write is
    several file events)."""
    if key in pending:
        GLib.source_remove(pending[key])
    pending[key] = GLib.timeout_add(ms, lambda: (pending.pop(key, None), fn(), False)[2])


def throttle(key, fn, ms):
    """Runs fn ms after the first call with this key; calls in between
    join that run (so it sees them all) instead of pushing it back."""
    if key not in pending:
        pending[key] = GLib.timeout_add(ms, lambda: (pending.pop(key, None), fn(), False)[2])


def dev_ports():
    """dev-ports sets tmux's @dev_ports."""
    return run_once("dev-ports", "--set-tmux")


claude_last = None   # the (text, class) last set: skip tmux when unchanged


def set_claude_limit(line):
    """@claude_limit from one `vesha waybar` line (JSON)."""
    import json
    global claude_last
    try:
        d = json.loads(line)
        text, cls = d.get("text", ""), d.get("class", "")
    except ValueError:
        text, cls = "", ""
    if (text, cls) == claude_last:
        return
    claude_last = (text, cls)
    if text and cls in ("ok", "warn", "full"):
        tmux("set", "-g", "@claude_limit", text)
        tmux("set", "-g", "@claude_limit_class", cls)
    else:   # one account, or usage unknown: nothing worth a capsule
        tmux("set", "-gu", "@claude_limit")
    tmux("refresh-client", "-S")


def claude_limit_line(stream, result, proc):
    """One line from `vesha waybar`: the active account and its 5-hour usage."""
    try:
        line, _ = stream.read_line_finish_utf8(result)
    except GLib.Error:
        line = None
    if line is None:   # vesha stopped (or isn't installed): hide the capsule, retry later
        global claude_last
        claude_last = None
        tmux("set", "-gu", "@claude_limit")
        GLib.timeout_add_seconds(300, watch_claude_limit)
        return
    set_claude_limit(line)
    stream.read_line_async(GLib.PRIORITY_DEFAULT, None, claude_limit_line, proc)


VESHA = os.path.expanduser("~/.local/bin/vesha")


def claude_limit_stream():
    """The fallback for a vesha before `waybar --sources`: its `vesha
    waybar` stream, a whole interpreter kept running for the line."""
    try:
        proc = Gio.Subprocess.new([VESHA, "waybar"], Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error as e:
        log("vesha waybar:", e.message)
        return False
    stream = Gio.DataInputStream.new(proc.get_stdout_pipe())
    stream.read_line_async(GLib.PRIORITY_DEFAULT, None, claude_limit_line, proc)
    return False


def claude_limit_once():
    """Runs `vesha waybar --once` in the background (it can fetch usage
    when the cache is old) and sets the capsule from its line."""
    if "vesha" in busy:
        again.add("vesha")
        return False
    try:
        proc = Gio.Subprocess.new([VESHA, "waybar", "--once"],
                                  Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error as e:
        log("vesha waybar --once:", e.message)
        return False
    busy.add("vesha")

    def done(p, result):
        busy.discard("vesha")
        try:
            _, out, _ = p.communicate_utf8_finish(result)
        except GLib.Error as e:
            log("vesha waybar --once:", e.message)
            out = None
        if p.get_if_exited() and p.get_exit_status() == 0 and out and out.strip():
            set_claude_limit(out.strip().splitlines()[-1])
        elif p.get_if_exited() and p.get_exit_status():
            log(f"vesha waybar --once exited with status {p.get_exit_status()}")
        if "vesha" in again:
            again.discard("vesha")
            claude_limit_once()
    proc.communicate_utf8_async(None, None, done)
    return False


limited = {}   # key -> monotonic time of its last run (rate_limit)


def rate_limit(key, fn, ms, settle=500):
    """Runs fn soon (settle ms after the call, so one write's several events
    are one run), but at most once every ms: a call inside that window runs
    fn when it ends, once, however many calls came."""
    if key in pending:
        return
    now = GLib.get_monotonic_time() // 1000
    wait = max(settle, limited.get(key, -ms) + ms - now)

    def run():
        pending.pop(key, None)
        limited[key] = GLib.get_monotonic_time() // 1000
        fn()
        return False
    pending[key] = GLib.timeout_add(wait, run)


path_monitors = []   # kept alive, like gh_monitors


def watch_paths(paths, on_change):
    """Calls on_change(path) when one of these files is written, replaced
    (write-and-rename) or deleted, through a monitor on each one's folder.
    A folder that doesn't exist yet is waited for from its nearest existing
    parent (no polling), and watched once it appears."""
    paths = set(paths)
    wanted = {os.path.dirname(p) for p in paths}
    for m in path_monitors:
        m.cancel()
    path_monitors.clear()
    watched = set()
    for d in wanted:
        while not os.path.isdir(d) and os.path.dirname(d) != d:
            d = os.path.dirname(d)
        if d in watched:
            continue
        watched.add(d)
        try:
            m = Gio.File.new_for_path(d).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
        except GLib.Error as e:
            log(f"can't watch {d}:", e.message)
            continue

        def changed(_m, f, other, _event):
            for p in (f.get_path(), other.get_path() if other else None):
                if p in paths:
                    on_change(p)
                elif p and any(w == p or w.startswith(p + "/") for w in wanted - watched) and os.path.isdir(p):
                    # a folder on the way to a wanted one appeared: watch again from there
                    GLib.idle_add(lambda: (watch_paths(paths, on_change), on_change(None), False)[2])
        m.connect("changed", changed)
        path_monitors.append(m)


def claude_limit_sources(paths):
    """Follows the files the line comes from: the accounts and the config
    at once (a switch shows the moment it happens), the usage cache at
    most once a minute (the status line rewrites it while Claude works,
    and the stream it replaces looked once a minute)."""
    usage = next((p for p in paths if os.path.basename(p) == "usage.json"), None)

    def on_change(path):
        if path is not None and path == usage:
            rate_limit("vesha-usage", claude_limit_once, 60000)
        else:
            debounce("vesha", claude_limit_once, 300)
    watch_paths(paths, on_change)
    claude_limit_once()


def watch_claude_limit():
    """Asks vesha which files its bar line comes from (`vesha waybar
    --sources`); a vesha that doesn't know the flag treats it as `vesha
    waybar` and starts streaming JSON instead: then stream (the old way)."""
    if not os.access(VESHA, os.X_OK):
        return False
    try:
        proc = Gio.Subprocess.new([VESHA, "waybar", "--sources"],
                                  Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error as e:
        log("vesha waybar --sources:", e.message)
        return False
    stream = Gio.DataInputStream.new(proc.get_stdout_pipe())
    paths = []

    def got_line(s, result):
        try:
            line, _ = s.read_line_finish_utf8(result)
        except GLib.Error:
            line = None
        if line is not None and line.startswith("/"):
            paths.append(line)
            s.read_line_async(GLib.PRIORITY_DEFAULT, None, got_line)
            return
        if line is not None:   # JSON: an older vesha, streaming
            proc.force_exit()
            log("vesha has no `waybar --sources` (before v0.7.0): following `vesha waybar` instead")
            claude_limit_stream()
        elif paths:
            claude_limit_sources(paths)
        else:
            log("vesha waybar --sources printed nothing; following `vesha waybar` instead")
            claude_limit_stream()
    stream.read_line_async(GLib.PRIORITY_DEFAULT, None, got_line)
    return False


def watch_stations():
    """`iw event` prints "<dev>: new station <mac>" / "del station" as
    devices join or leave any access point on this machine (the hotspot)."""
    global iw_events
    try:
        iw_events = Gio.Subprocess.new(["iw", "event"],
                                       Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error as e:
        log("no `iw event`, hotspot capsule only updates on its timer:", e.message)
        return
    stream = Gio.DataInputStream.new(iw_events.get_stdout_pipe())

    def got_line(s, result):
        try:
            line, _ = s.read_line_finish_utf8(result)
        except GLib.Error:
            line = None
        if line is None:   # iw exited: follow again (else only the 30 s poll)
            log("iw event exited; restarting it in 10 s")
            GLib.timeout_add_seconds(10, lambda: (watch_stations(), False)[1])
            return
        if " station " in line:
            refresh("hotspot")
        s.read_line_async(GLib.PRIORITY_DEFAULT, None, got_line)

    stream.read_line_async(GLib.PRIORITY_DEFAULT, None, got_line)


# What `pactl subscribe` says when the output itself changes ("on sink #N",
# "on card #N", "on server"); a bare "sink" also matches every sink-input
# (each app's stream). The same match bar-volume makes when it streams.
PACTL_WATCH = re.compile(r"on (?:sink|card) #|on server\b")
pactl_retry = 1   # seconds before following the sound server again (2, 4... up to 60)


def watch_volume():
    """The sound capsule: `pactl subscribe`, refreshing on a change to the
    output. If the sound server goes away (pactl exits), follow it again
    after 2 s, then longer each time it fails at once, up to a minute."""
    try:
        proc = Gio.Subprocess.new(["pactl", "subscribe"],
                                  Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error as e:
        log("no `pactl`, the sound capsule only shows what it had at waybar's start:", e.message)
        return False
    started = GLib.get_monotonic_time()
    stream = Gio.DataInputStream.new(proc.get_stdout_pipe())

    def got_line(s, result):
        global pactl_retry
        try:
            line, _ = s.read_line_finish_utf8(result)
        except GLib.Error:
            line = None
        if line is None:
            # ran a while: the server restarted, come back quickly; else back off
            pactl_retry = 2 if GLib.get_monotonic_time() - started > 60_000_000 else min(pactl_retry * 2, 60)
            log(f"pactl subscribe exited; following the sound server again in {pactl_retry} s")
            GLib.timeout_add_seconds(pactl_retry, watch_volume)
            refresh("volume")
            return
        if PACTL_WATCH.search(line):
            refresh("volume")
        s.read_line_async(GLib.PRIORITY_DEFAULT, None, got_line)

    stream.read_line_async(GLib.PRIORITY_DEFAULT, None, got_line)
    refresh("volume")   # whatever changed while nothing followed it
    return False


def main():
    global docker_active
    if sys.argv[1:] == ["--tmux-narada"]:
        try:
            r = subprocess.run([NARADA, "status", "--json"], capture_output=True, text=True, timeout=15)
            set_narada(r.stdout if r.returncode == 0 else None)
        except (OSError, subprocess.TimeoutExpired) as e:
            log("narada status:", e)
        return
    if sys.argv[1:] == ["--tmux-claude"]:
        try:
            r = subprocess.run([os.path.expanduser("~/.local/bin/vesha"), "waybar", "--once"], check=False,
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and r.stdout.strip():
                set_claude_limit(r.stdout.strip().splitlines()[-1])
        except (OSError, subprocess.TimeoutExpired) as e:
            log("vesha waybar --once:", e)
        return
    if sys.argv[1:] == ["--tmux-docker"]:
        docker_active = subprocess.run(["systemctl", "is-active", "--quiet", "docker.service"]).returncode == 0
        tmux_docker()
        return

    session = Gio.bus_get_sync(Gio.BusType.SESSION)
    system = Gio.bus_get_sync(Gio.BusType.SYSTEM)

    session.signal_subscribe(None, "org.freedesktop.Notifications", "NotificationClosed", None,
                             None, Gio.DBusSignalFlags.NONE, lambda *a: refresh("bell"))
    session.signal_subscribe(None, "dev.vayu.Akashvani", "Changed", None,
                             None, Gio.DBusSignalFlags.NONE, lambda *a: refresh("bell"))

    settings = Gio.Settings.new("org.gnome.desktop.interface")
    settings.connect("changed::color-scheme", lambda *a: refresh("theme"))

    watch_unit(session, "swayidle.service",
               lambda s: s in ("active", "inactive", "failed") and refresh("jyoti"))
    watch_unit(session, "ekatva.service",
               lambda s: s in ("active", "inactive", "failed") and refresh("ekatva"))

    watch_unit(system, "docker.service", on_docker_state)

    # Hotspot: a connection going up or down, and devices joining/leaving
    # (`iw event` needs no root; NM's leases folder is root-only).
    system.signal_subscribe(NM, "org.freedesktop.DBus.Properties", "PropertiesChanged",
                            "/org/freedesktop/NetworkManager", None, Gio.DBusSignalFlags.NONE,
                            lambda c, s, p, i, m, params: "ActiveConnections" in params.unpack()[1]
                            and refresh("hotspot"))
    watch_stations()
    watch_volume()

    gh_reviews()
    GLib.timeout_add_seconds(120, gh_reviews)
    watch_gh_account()
    tmux_narada()
    watch_narada()
    GLib.timeout_add_seconds(120, lambda: (tmux_narada(), True)[1])   # if the watch misses one
    dev_ports()
    GLib.timeout_add_seconds(15, dev_ports)
    watch_claude_limit()

    # Whatever changed while this wasn't running.
    for name in WAYBAR_SIGNAL:
        refresh(name)
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
