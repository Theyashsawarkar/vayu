#!/usr/bin/env python3
"""Bar events: refreshes waybar capsules, and tmux's docker count, when the
thing they show changes -- instead of each capsule polling on a timer.
Systemd user unit bar-events.service, started by sway after waybar.

  capsule     waybar signal   event
  bell        8               org.freedesktop.Notifications NotificationClosed
                              (the history grows when one closes), and
                              akashvani's dev.vayu.Akashvani Changed (modes:
                              do not disturb from the panel, a timer, a key)
  jyoti       12              swayidle.service ActiveState (user systemd),
                              and ~/.local/state/jyoti/enabled (its level)
  ekatva      13              ekatva.service ActiveState (user systemd)
  docker      14              docker.service ActiveState (system systemd),
                              then `docker events` start/die while it runs
  hotspot     15              NetworkManager's ActiveConnections, and
                              `iw event` new/del station (a device joined
                              or left the hotspot)
  volume      17              Vyom's sound state (dev.vayu.Vyom.State's
                              volume on D-Bus: vyom/live.py already follows
                              the sound server), or, while Vyom isn't
                              running or publishing it, `pactl subscribe`
                              here: the output itself changed (a sink, a
                              card, the server's default), not each app's
                              stream; the line is built here with
                              bar-volume's from_state() / line()

tmux's pull request capsule (@gh_reviews, @gh_prs) is set from gh-review-count every
2 minutes (GitHub has no push for "review requested" to a desktop), and
right away when the account it counts changes -- gh's hosts.yml (gh auth
switch), sangam's last-account (u in sangam) -- or sangam says PRs changed
(~/.cache/sangam/changed: a merge, review or reload there, or by an agent
through `sangam mcp`). Its unread mail and chat capsule (@narada_mail,
@narada_chat) follows narada's local copy (its database changes when a
sync brings mail or you read something), asking `narada status`; WhatsApp
gets its own green capsule (@narada_whatsapp). Its dev
servers capsule (@dev_ports) from dev-ports' code loaded here, every 15
seconds (listening sockets have no event): two /proc reads, and process
mapping plus one tmux call only when the listening set changed. Its Claude limit capsule (@claude_limit, and
@claude_limit_class ok/warn/full) runs `vesha waybar --once` when one of
the files `vesha waybar --sources` names changes: the accounts (a switch,
at once) and the usage cache (at most once a minute, as the stream did). A
vesha without --sources (before v0.7.0) is followed through `vesha waybar`,
which prints a line whenever the account or its usage changes.

Caps Lock / Num Lock (9, 10) are signalled by sway's --release binds and
keylock-toggle.sh. Everything else on the bar is waybar-internal.

bell, jyoti, ekatva, docker and volume: this daemon writes the capsule's
line to $XDG_RUNTIME_DIR/vayu/bar/<name>.json (write and rename) and
signals waybar only when it changed; waybar's exec is a `cat` of that file,
the script itself only when the file is missing (this daemon isn't
running; it removes the files when it stops). The scripts still build the
text (run here, off waybar); the sound line is built in-process, without
a debounce, so a scroll step shows as soon as Vyom (or pactl) answers.
Vyom follows the sound server anyway, so with it there is one `pactl
subscribe` on the desktop, not two, and a step runs one pactl, not three
(Vyom's and this daemon's own); when Vyom goes (or an older Vyom doesn't
publish the output's kind) this daemon follows pactl itself again. hotspot is
still only signalled (its script runs in waybar). The first event after
a quiet spell refreshes at once; bursts (compose starts several
containers) collapse into one more refresh 0.3 s after the last event. Children that follow something (`pactl subscribe`, `iw
event`, `docker events`) run under `setpriv --pdeathsig`, so they die with
this daemon even when it is killed.

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

WAYBAR_SIGNAL = {"bell": 8, "jyoti": 12, "ekatva": 13, "docker": 14, "hotspot": 15, "volume": 17}
# Capsules whose line this daemon writes to BAR_DIR/<name>.json, so waybar's
# exec on the signal is a `cat` of it (falling back to the script when the
# file is missing). The script still builds the line (it stays the one
# place its text lives, and kendra or waybar alone can run it); it runs
# here, off waybar, once per event, and waybar is signalled only when the
# line changed. The sound capsule is built in-process (watch_volume).
BIN = os.path.dirname(os.path.realpath(__file__))
CAPSULE_SCRIPT = {"bell": "notification-history-status.sh", "jyoti": "jyoti-status.sh",
                  "ekatva": "ekatva-status.sh", "docker": "docker-status.sh"}
BAR_DIR = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}", "vayu", "bar")
NM = "org.freedesktop.NetworkManager"
iw_events = None  # the running `iw event` Gio.Subprocess
SD = "org.freedesktop.systemd1"

pending = {}          # capsule -> GLib source id of its scheduled refresh
fired = {}            # capsule -> monotonic µs of its last refresh
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
    """The first event after a quiet spell refreshes at once (a dismissed
    notification, Jyoti switched: the capsule follows in ~20 ms, not 300+);
    events within 0.3 s of the last refresh collapse into one more, 0.3 s
    after the last of them (compose starting several containers)."""
    now = GLib.get_monotonic_time()
    if name not in pending and now - fired.get(name, 0) >= 300_000:
        fired[name] = now
        fire(name)
        return
    if name in pending:
        GLib.source_remove(pending[name])
    pending[name] = GLib.timeout_add(300, trailing, name)


def trailing(name):
    fired[name] = GLib.get_monotonic_time()
    return fire(name)


def fire(name):
    pending.pop(name, None)
    args = []
    if name == "docker":
        args = [str(tmux_docker())]   # docker-status.sh takes the count: no second `docker ps`
    if name in CAPSULE_SCRIPT:
        run_capsule(name, args)
    elif name == "volume":
        volume_line()
    else:
        signal_waybar(WAYBAR_SIGNAL[name])
    return False


def write_capsule(name, line):
    """Writes a capsule's line to BAR_DIR/<name>.json (write and rename, so
    waybar's cat never reads half of it). Returns whether it changed."""
    path = os.path.join(BAR_DIR, f"{name}.json")
    line = line.rstrip("\n") + "\n"
    try:
        with open(path) as f:
            if f.read() == line:
                return False
    except OSError:
        pass
    try:
        os.makedirs(BAR_DIR, exist_ok=True)
        with open(path + ".tmp", "w") as f:
            f.write(line)
        os.replace(path + ".tmp", path)
    except OSError as e:
        log(f"can't write {path}:", e)
    return True


def clear_capsules(*_):
    """On stop: remove the lines, so waybar runs the scripts itself again
    instead of showing what this daemon last saw."""
    for name in (*CAPSULE_SCRIPT, "volume"):
        try:
            os.unlink(os.path.join(BAR_DIR, f"{name}.json"))
        except OSError:
            pass
    loop.quit()
    return False


def run_capsule(name, args=()):
    """Runs the capsule's script in the background, writes its line, and
    signals waybar if it changed. A refresh asked for while it runs runs
    once more after it (the state moved on meanwhile)."""
    key = f"capsule-{name}"
    if key in busy:
        again.add(key)
        return
    try:
        proc = Gio.Subprocess.new([os.path.join(BIN, CAPSULE_SCRIPT[name]), *args],
                                  Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error as e:
        log(f"{CAPSULE_SCRIPT[name]}:", e.message)
        signal_waybar(WAYBAR_SIGNAL[name])   # waybar's exec runs it itself, if it can
        return
    busy.add(key)

    def done(p, result):
        busy.discard(key)
        try:
            _, out, _ = p.communicate_utf8_finish(result)
        except GLib.Error as e:
            log(f"{CAPSULE_SCRIPT[name]}:", e.message)
            out = None
        lines = (out or "").strip().splitlines()
        if lines and write_capsule(name, lines[-1]):
            signal_waybar(WAYBAR_SIGNAL[name])
        elif not lines:
            log(f"{CAPSULE_SCRIPT[name]} printed nothing")
        if key in again:
            again.discard(key)
            fire(name)
    proc.communicate_utf8_async(None, None, done)


def watcher(argv):
    """argv for a child that follows something for as long as this daemon
    runs (`pactl subscribe`, `iw event`, `docker events`...): through
    setpriv --pdeathsig, so it gets SIGTERM if this daemon dies, even by
    SIGKILL, instead of living on as an orphan (one did, a whole day)."""
    setpriv = "/usr/bin/setpriv"
    return [setpriv, "--pdeathsig", "TERM", "--", *argv] if os.access(setpriv, os.X_OK) else list(argv)


def signal_waybar(n):
    """Sends SIGRTMIN+n to waybar, but only to one that already catches it
    (SigCgt in /proc). An RT signal's default action is to terminate, so
    one sent while waybar is still starting kills the bar -- which this
    daemon's startup refresh did at login. A starting waybar runs every
    capsule script anyway. Same check as the waybar-signal script."""
    sig = signal.SIGRTMIN + n
    known = [p for p in waybar_pids if waybar_status(p) is not None]
    pids = known or [p for p in filter(str.isdigit, os.listdir("/proc")) if waybar_status(p) is not None]
    waybar_pids[:] = pids   # the next refresh skips the /proc walk (a few ms)
    for pid in pids:
        try:
            if int(waybar_status(pid), 16) >> (sig - 1) & 1:
                os.kill(int(pid), sig)
        except (OSError, TypeError, ValueError):
            pass  # exited meanwhile


waybar_pids = []


def waybar_status(pid):
    """SigCgt of a waybar process, None for anything else."""
    try:
        with open(f"/proc/{pid}/status") as f:
            fields = dict(line.split(":", 1) for line in f if line.startswith(("Name:", "SigCgt:")))
    except OSError:
        return None   # exited, or not ours to read
    return fields.get("SigCgt", "").strip() if fields.get("Name", "").strip() == "waybar" else None


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
    return count


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
        docker_events = Gio.Subprocess.new(watcher(
            ["docker", "events", "--filter", "type=container", "--filter", "event=start",
             "--filter", "event=die", "--format", "{{.Action}}"]),
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


dev_ports_watch = None   # dev-ports' Watch, loaded once; None: run the script instead


def load_dev_ports():
    """dev-ports' code in this process: a look is two /proc reads (~2 ms)
    and starts nothing, where running the script every 15 s cost a Python
    start (~35 ms). Falls back to the script if it can't be loaded."""
    global dev_ports_watch, dev_ports_mod
    import importlib.machinery
    import importlib.util
    path = os.path.expanduser("~/.local/bin/dev-ports")
    try:
        loader = importlib.machinery.SourceFileLoader("dev_ports", path)
        spec = importlib.util.spec_from_loader("dev_ports", loader)
        dev_ports_mod = importlib.util.module_from_spec(spec)
        loader.exec_module(dev_ports_mod)
        dev_ports_watch = dev_ports_mod.Watch()
    except Exception as e:   # an older dev-ports (no Watch) or a broken file
        log("dev-ports: running the script instead:", e)
        dev_ports_watch = None


def dev_ports():
    """Sets tmux's @dev_ports when the listening sockets changed."""
    if dev_ports_watch is None:
        return run_once("dev-ports", "--set-tmux")
    try:
        items = dev_ports_watch.poll()
        if items is not None:
            dev_ports_mod.set_tmux(items)
    except Exception as e:
        log("dev-ports:", e)
    return True


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
        proc = Gio.Subprocess.new(watcher([VESHA, "waybar"]), Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
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


path_monitors = {}   # key -> its monitors, kept alive like gh_monitors


def watch_paths(key, paths, on_change):
    """Calls on_change(path) when one of these files is written, replaced
    (write-and-rename) or deleted, through a monitor on each one's folder.
    A folder that doesn't exist yet is waited for from its nearest existing
    parent (no polling), and watched once it appears."""
    paths = set(paths)
    wanted = {os.path.dirname(p) for p in paths}
    for m in path_monitors.pop(key, []):
        m.cancel()
    mine = path_monitors.setdefault(key, [])
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
                    GLib.idle_add(lambda: (watch_paths(key, paths, on_change), on_change(None), False)[2])
        m.connect("changed", changed)
        mine.append(m)


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
    watch_paths("vesha", paths, on_change)
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
        iw_events = Gio.Subprocess.new(watcher(["iw", "event"]),
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
bar_volume = None  # bar-volume, imported: its line() builds the capsule


def load_bar_volume():
    """bar-volume (beside this file) as a module, for its line(): the one
    place the sound capsule's look lives."""
    global bar_volume
    from importlib.machinery import SourceFileLoader
    from importlib.util import module_from_spec, spec_from_loader
    try:
        loader = SourceFileLoader("bar_volume", os.path.join(BIN, "bar-volume"))
        mod = module_from_spec(spec_from_loader("bar_volume", loader))
        loader.exec_module(mod)
        bar_volume = mod
    except (OSError, SyntaxError, ImportError) as e:
        log("can't load bar-volume; waybar runs it itself on each change:", e)


def volume_line():
    """Asks the sound server for the default sink and the sinks (two pactl
    runs side by side, ~10 ms, off the main loop), builds the line with
    bar-volume's line(), writes it and signals waybar if it changed. No
    debounce: a scroll step shows as soon as pactl answers; steps that come
    while it asks are one more run after it."""
    if bar_volume is None:
        signal_waybar(WAYBAR_SIGNAL["volume"])   # waybar's exec falls back to `bar-volume --once`
        return
    if "volume" in busy:
        again.add("volume")
        return
    busy.add("volume")
    answers = {}

    def ask(key, *args):
        try:
            p = Gio.Subprocess.new(["pactl", "-f", "json", *args],
                                   Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
        except GLib.Error as e:
            log("pactl:", e.message)
            answers[key] = ""
            return

        def done(proc, result):
            try:
                _, out, _ = proc.communicate_utf8_finish(result)
            except GLib.Error:
                out = ""
            answers[key] = out or ""
            if len(answers) == 2:
                finish()
        p.communicate_utf8_async(None, None, done)

    def finish():
        import json
        busy.discard("volume")
        try:
            default = json.loads(answers["info"] or "{}").get("default_sink_name", "")
            sinks = json.loads(answers["sinks"] or "[]")
            line = json.dumps(bar_volume.line(default, sinks), ensure_ascii=False)
        except (ValueError, AttributeError, KeyError, TypeError) as e:
            log("sound capsule:", e)
            line = None
        if line and write_capsule("volume", line):
            signal_waybar(WAYBAR_SIGNAL["volume"])
        if "volume" in again:
            again.discard("volume")
            volume_line()

    ask("info", "info")
    ask("sinks", "list", "sinks")
    if len(answers) == 2:   # both failed to start
        finish()


volume_proc = None    # our own `pactl subscribe`, while Vyom doesn't follow the sound for us
volume_gen = 0        # bumped when we stop following ourselves: the old watcher's exit is no news
via_vyom = False      # the capsule comes from Vyom's state right now


def watch_volume():
    """The sound capsule without Vyom: `pactl subscribe`, a new line on a
    change to the output. If the sound server goes away (pactl exits),
    follow it again after 2 s, then longer each time it fails at once, up to
    a minute."""
    global volume_proc
    if via_vyom or volume_proc is not None:
        return False
    try:
        proc = Gio.Subprocess.new(watcher(["pactl", "subscribe"]),
                                  Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error as e:
        log("no `pactl`, the sound capsule only shows what it had at waybar's start:", e.message)
        return False
    volume_proc = proc
    gen = volume_gen
    started = GLib.get_monotonic_time()
    stream = Gio.DataInputStream.new(proc.get_stdout_pipe())

    def got_line(s, result):
        global pactl_retry, volume_proc
        try:
            line, _ = s.read_line_finish_utf8(result)
        except GLib.Error:
            line = None
        if gen != volume_gen:   # stopped on purpose: Vyom follows the sound now
            return
        if line is None:
            volume_proc = None
            # ran a while: the server restarted, come back quickly; else back off
            pactl_retry = 2 if GLib.get_monotonic_time() - started > 60_000_000 else min(pactl_retry * 2, 60)
            log(f"pactl subscribe exited; following the sound server again in {pactl_retry} s")
            GLib.timeout_add_seconds(pactl_retry, watch_volume)
            volume_line()
            return
        if PACTL_WATCH.search(line):
            volume_line()
        s.read_line_async(GLib.PRIORITY_DEFAULT, None, got_line)

    stream.read_line_async(GLib.PRIORITY_DEFAULT, None, got_line)
    volume_line()   # whatever changed while nothing followed it
    return False


def stop_watch_volume():
    global volume_proc, volume_gen
    volume_gen += 1
    if volume_proc is not None:
        volume_proc.send_signal(signal.SIGTERM)   # setpriv passes it on to pactl
        volume_proc.wait_async(None, None)        # reaped when it's gone
        volume_proc = None


VYOM = "dev.vayu.Vyom"
VYOM_STATE = "/dev/vayu/Vyom/State"
VYOM_IFACE = "dev.vayu.Vyom.State"


def vyom_volume(text):
    """Vyom's published sound state (JSON text): writes the capsule from it
    and returns True, or False when it can't be used (Vyom doesn't follow
    the sound server yet, or is older and leaves out the output's kind)."""
    import json
    if bar_volume is None or not hasattr(bar_volume, "from_state"):
        return False
    try:
        st = json.loads(text) if text else None
    except ValueError:
        st = None
    if not isinstance(st, dict) or "sink" not in st:
        return False
    try:
        line = json.dumps(bar_volume.from_state(st), ensure_ascii=False)
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        log("sound capsule from vyom:", e)
        return False
    if write_capsule("volume", line):
        signal_waybar(WAYBAR_SIGNAL["volume"])
    return True


def use_vyom_volume(text):
    """Follows Vyom's sound state when it's usable, else our own pactl."""
    global via_vyom
    if vyom_volume(text):
        if not via_vyom:
            via_vyom = True
            stop_watch_volume()
            log("the sound capsule follows Vyom's state")
    elif via_vyom or volume_proc is None:
        if via_vyom:
            log("Vyom doesn't publish the sound state; following pactl here")
        via_vyom = False
        watch_volume()


def follow_vyom(session):
    """The sound capsule from Vyom's live state while Vyom runs (its
    PropertiesChanged on dev.vayu.Vyom.State, routed only from Vyom), our
    own `pactl subscribe` while it doesn't."""
    def changed(_c, _sender, _path, _iface, _member, params):
        iface, props, _ = params.unpack()
        if iface == VYOM_IFACE and "volume" in props:
            use_vyom_volume(props["volume"])

    session.signal_subscribe(VYOM, "org.freedesktop.DBus.Properties", "PropertiesChanged", VYOM_STATE,
                             VYOM_IFACE, Gio.DBusSignalFlags.NONE, changed)

    def appeared(conn, _name, _owner):
        def got(c, res):
            try:
                text = c.call_finish(res).unpack()[0]
            except GLib.Error:
                text = None   # no state exported (an older Vyom, or `live = false`)
            use_vyom_volume(text)
        conn.call(VYOM, VYOM_STATE, "org.freedesktop.DBus.Properties", "Get",
                  GLib.Variant("(ss)", (VYOM_IFACE, "volume")), GLib.VariantType("(v)"),
                  Gio.DBusCallFlags.NO_AUTO_START, 2000, None, got)

    Gio.bus_watch_name_on_connection(session, VYOM, Gio.BusNameWatcherFlags.NONE, appeared,
                                     lambda *_: use_vyom_volume(None))


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
    load_bar_volume()
    follow_vyom(session)   # then Vyom's state, or watch_volume() without it

    gh_reviews()
    GLib.timeout_add_seconds(120, gh_reviews)
    watch_gh_account()
    tmux_narada()
    watch_narada()
    GLib.timeout_add_seconds(120, lambda: (tmux_narada(), True)[1])   # if the watch misses one
    load_dev_ports()
    dev_ports()
    GLib.timeout_add_seconds(15, dev_ports)
    watch_claude_limit()

    # jyoti's level ("high": Nandādīpa) is a file ekatva and jyoti-toggle.sh write
    jyoti_state = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"),
                               "jyoti", "enabled")
    watch_paths("jyoti", [jyoti_state], lambda _p: refresh("jyoti"))

    # Whatever changed while this wasn't running (volume: watch_volume did).
    for name in WAYBAR_SIGNAL:
        if name != "volume":
            refresh(name)
    try:   # GLib 2.80 moved it
        from gi.repository import GLibUnix
        signal_add = GLibUnix.signal_add
    except ImportError:
        signal_add = GLib.unix_signal_add
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal_add(GLib.PRIORITY_HIGH, sig, clear_capsules)
    loop.run()


loop = GLib.MainLoop()

if __name__ == "__main__":
    main()
