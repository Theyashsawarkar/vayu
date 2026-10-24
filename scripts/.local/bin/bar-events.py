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

tmux's "to review" capsule (@gh_reviews) is set from gh-review-count every
5 minutes (GitHub has no push for "review requested" to a desktop). Its dev
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
(tmux.conf runs it on load, since tmux can start after this daemon).
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


def run_once(name, *args):
    """Starts a helper in the background unless its last run is still going
    (a hung `gh api` used to pile up a new one every 5 minutes). Its stderr
    goes to this service's journal. Returns True to keep the GLib timer."""
    if name in busy:
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
        try:
            p.wait_finish(result)
            if p.get_if_exited() and p.get_exit_status():
                log(f"{name} exited with status {p.get_exit_status()}")
        except GLib.Error as e:
            log(f"{name}:", e.message)
    proc.wait_async(None, done)
    return True


def gh_reviews():
    """gh-review-count sets tmux's @gh_reviews."""
    return run_once("gh-review-count", "--set-tmux")


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
    GLib.timeout_add_seconds(300, gh_reviews)
    dev_ports()
    GLib.timeout_add_seconds(15, dev_ports)
    watch_claude_limit()

    # Whatever changed while this wasn't running.
    for name in WAYBAR_SIGNAL:
        refresh(name)
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
