#!/usr/bin/env python3
"""Bar events: refreshes waybar capsules, and tmux's docker count, when the
thing they show changes -- instead of each capsule polling on a timer.
Systemd user unit bar-events.service, started by sway after waybar.

  capsule     waybar signal   event
  bell        8               org.freedesktop.Notifications NotificationClosed
                              (mako's history only grows when one closes;
                              mode changes signal from notification-mode.sh)
  theme       11              GSettings color-scheme changed (dconf)
  caffeine    12              swayidle.service ActiveState (user systemd)
  phone       13              KDE Connect device/battery/daemon signals, and
                              kdeconnectd appearing on / leaving the bus
  docker      14              docker.service ActiveState (system systemd),
                              then `docker events` start/die while it runs
  hotspot     15              NetworkManager's ActiveConnections, and
                              `iw event` new/del station (a device joined
                              or left the hotspot)

tmux's pull request capsule (@gh_reviews, @gh_prs) is set from gh-review-count every
2 minutes (GitHub has no push for "review requested" to a desktop), and
right away when the account it counts changes -- gh's hosts.yml (gh auth
switch), sangam's last-account (u in sangam) -- or sangam says PRs changed
(~/.cache/sangam/changed: a merge, review or reload there, or by an agent
through `sangam mcp`). Its unread mail and chat capsule (@sandesh_mail,
@sandesh_chat) follows sandesh's local copy (its database changes when a
sync brings mail or you read something), asking `sandesh status`. Its dev
servers capsule (@dev_ports) from dev-ports every 15 seconds (listening
sockets have no event). Its Claude limit capsule (@claude_limit, and
@claude_limit_class ok/warn/full) follows `vesha waybar`, which prints a
line whenever the active account or its usage changes.

Caps Lock / Num Lock (9, 10) are signalled by sway's --release binds and
keylock-toggle.sh. Everything else on the bar is waybar-internal.

Each capsule's own script still builds its text; this only says "now".
Bursts (a phone connecting sends reachableChanged then battery refreshed;
compose starts several containers) collapse into one refresh 0.3 s after
the last event.

`bar-events.py --tmux-docker` sets tmux's @docker_count once and exits
(tmux.conf runs it on load, since tmux can start after this daemon);
`--tmux-sandesh` the same for @sandesh_mail and @sandesh_chat.
"""
import os
import signal
import subprocess
import sys

from gi.repository import Gio, GLib

WAYBAR_SIGNAL = {"bell": 8, "theme": 11, "caffeine": 12, "phone": 13, "docker": 14, "hotspot": 15}
NM = "org.freedesktop.NetworkManager"
iw_events = None  # the running `iw event` Gio.Subprocess
KDECONNECT = "org.kde.kdeconnect"
PHONE_SIGNALS = [  # (interface, member)
    (f"{KDECONNECT}.device", "reachableChanged"),
    (f"{KDECONNECT}.device", "pairStateChanged"),
    (f"{KDECONNECT}.device", "nameChanged"),
    (f"{KDECONNECT}.device.battery", "refreshed"),
    (f"{KDECONNECT}.daemon", "pairingRequestsChanged"),
    (f"{KDECONNECT}.daemon", "deviceListChanged"),
]
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
    pending[name] = GLib.timeout_add(300, fire, name)


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


SANDESH = os.path.expanduser("~/.local/bin/sandesh")
sandesh_monitor = None  # kept alive, like gh_monitors


def set_sandesh(out):
    """@sandesh_mail / @sandesh_chat from `sandesh status --json` output;
    unset (no capsule) when sandesh can't say."""
    import json
    try:
        d = json.loads(out or "")
        mail, chat = int(d.get("mail", 0)), int(d.get("chat", 0))
    except (ValueError, TypeError, AttributeError):
        tmux("set", "-gu", "@sandesh_mail")
        tmux("set", "-gu", "@sandesh_chat")
        return
    tmux("set", "-g", "@sandesh_mail", str(mail))
    tmux("set", "-g", "@sandesh_chat", str(chat))


def tmux_sandesh():
    """Asks sandesh for its unread counts (its local copy, no network) in
    the background: SQLite can wait on a sync's write lock."""
    if not os.access(SANDESH, os.X_OK):
        return False
    if "sandesh" in busy:
        again.add("sandesh")
        return False
    try:
        proc = Gio.Subprocess.new([SANDESH, "status", "--json"],
                                  Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error as e:
        log("sandesh status:", e.message)
        return False
    busy.add("sandesh")

    def done(p, result):
        busy.discard("sandesh")
        try:
            _, out, _ = p.communicate_utf8_finish(result)
        except GLib.Error as e:
            log("sandesh status:", e.message)
            out = None
        if p.get_if_exited() and p.get_exit_status() == 0:
            set_sandesh(out)
        if "sandesh" in again:
            again.discard("sandesh")
            tmux_sandesh()
    proc.communicate_utf8_async(None, None, done)
    return False


def watch_sandesh():
    """sandesh's data folder: its database (and WAL) change on every sync
    write and every read/unread, from the screen, the CLI or an agent."""
    global sandesh_monitor
    data = os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "sandesh")
    try:
        sandesh_monitor = Gio.File.new_for_path(data).monitor_directory(Gio.FileMonitorFlags.NONE, None)
    except GLib.Error as e:
        log(f"can't watch {data}, the mail capsule updates every 2 minutes only:", e.message)
        return
    sandesh_monitor.set_rate_limit(1000)
    sandesh_monitor.connect("changed", lambda *a: debounce("sandesh", tmux_sandesh, 1000))


def debounce(key, fn, ms=500):
    """Runs fn once, ms after the last call with this key (a write is
    several file events)."""
    if key in pending:
        GLib.source_remove(pending[key])
    pending[key] = GLib.timeout_add(ms, lambda: (pending.pop(key, None), fn(), False)[2])


def dev_ports():
    """dev-ports sets tmux's @dev_ports."""
    return run_once("dev-ports", "--set-tmux")


def claude_limit_line(stream, result, proc):
    """One line from `vesha waybar`: the active account and its 5-hour usage."""
    import json
    try:
        line, _ = stream.read_line_finish_utf8(result)
    except GLib.Error:
        line = None
    if line is None:   # vesha stopped (or isn't installed): hide the capsule, retry later
        tmux("set", "-gu", "@claude_limit")
        GLib.timeout_add_seconds(300, watch_claude_limit)
        return
    try:
        d = json.loads(line)
        text, cls = d.get("text", ""), d.get("class", "")
    except ValueError:
        text, cls = "", ""
    if text and cls in ("ok", "warn", "full"):
        tmux("set", "-g", "@claude_limit", text)
        tmux("set", "-g", "@claude_limit_class", cls)
    else:   # one account, or usage unknown: nothing worth a capsule
        tmux("set", "-gu", "@claude_limit")
    tmux("refresh-client", "-S")
    stream.read_line_async(GLib.PRIORITY_DEFAULT, None, claude_limit_line, proc)


def watch_claude_limit():
    vesha = os.path.expanduser("~/.local/bin/vesha")
    if not os.access(vesha, os.X_OK):
        return False
    try:
        proc = Gio.Subprocess.new([vesha, "waybar"], Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error as e:
        log("vesha waybar:", e.message)
        return False
    stream = Gio.DataInputStream.new(proc.get_stdout_pipe())
    stream.read_line_async(GLib.PRIORITY_DEFAULT, None, claude_limit_line, proc)
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


def main():
    global docker_active
    if sys.argv[1:] == ["--tmux-sandesh"]:
        try:
            r = subprocess.run([SANDESH, "status", "--json"], capture_output=True, text=True, timeout=15)
            set_sandesh(r.stdout if r.returncode == 0 else None)
        except (OSError, subprocess.TimeoutExpired) as e:
            log("sandesh status:", e)
        return
    if sys.argv[1:] == ["--tmux-docker"]:
        docker_active = subprocess.run(["systemctl", "is-active", "--quiet", "docker.service"]).returncode == 0
        tmux_docker()
        return

    session = Gio.bus_get_sync(Gio.BusType.SESSION)
    system = Gio.bus_get_sync(Gio.BusType.SYSTEM)

    session.signal_subscribe(None, "org.freedesktop.Notifications", "NotificationClosed", None,
                             None, Gio.DBusSignalFlags.NONE, lambda *a: refresh("bell"))

    settings = Gio.Settings.new("org.gnome.desktop.interface")
    settings.connect("changed::color-scheme", lambda *a: refresh("theme"))

    watch_unit(session, "swayidle.service",
               lambda s: s in ("active", "inactive", "failed") and refresh("caffeine"))

    for iface, member in PHONE_SIGNALS:
        session.signal_subscribe(None, iface, member, None, None, Gio.DBusSignalFlags.NONE,
                                 lambda *a: refresh("phone"))
    # Appeared/vanished also fire once now, which covers the startup refresh.
    Gio.bus_watch_name_on_connection(session, KDECONNECT, Gio.BusNameWatcherFlags.NONE,
                                     lambda *a: refresh("phone"), lambda *a: refresh("phone"))

    watch_unit(system, "docker.service", on_docker_state)

    # Hotspot: a connection going up or down, and devices joining/leaving
    # (`iw event` needs no root; NM's leases folder is root-only).
    system.signal_subscribe(NM, "org.freedesktop.DBus.Properties", "PropertiesChanged",
                            "/org/freedesktop/NetworkManager", None, Gio.DBusSignalFlags.NONE,
                            lambda c, s, p, i, m, params: "ActiveConnections" in params.unpack()[1]
                            and refresh("hotspot"))
    watch_stations()

    gh_reviews()
    GLib.timeout_add_seconds(120, gh_reviews)
    watch_gh_account()
    tmux_sandesh()
    watch_sandesh()
    GLib.timeout_add_seconds(120, lambda: (tmux_sandesh(), True)[1])   # if the watch misses one
    dev_ports()
    GLib.timeout_add_seconds(15, dev_ports)
    watch_claude_limit()

    # Whatever changed while this wasn't running.
    for name in WAYBAR_SIGNAL:
        refresh(name)
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
