#!/usr/bin/env python3
"""Docker picker for waybar's docker module. Replaces nwg-bar's docker.json
(a static two-button menu: Stats, Stop All) -- asked for directly: that
menu couldn't show anything about which containers are actually running,
which is the one thing you'd actually want to glance at. nwg-bar can't do
dynamic content at all (confirmed elsewhere in this repo, see
ARCHITECTURE.md's nwg-bar section), so this is the same wofi-popup
approach as wifi-picker.py/bluetooth-picker.py instead.

One info row per running container (name, image, status, ports -- view
only, selecting it just shows the same info again via notify-send, it's
not destructive) plus two action rows right after it (Stop, Restart).
Deliberately not a single "click to stop" row the way bluetooth-picker.py's
device rows work -- asked for viewing and separate stop/restart actions,
not a single combined toggle.
"""
import subprocess
import sys

WOFI_PROMPT = "Docker"

# Same Catppuccin Mocha convention as wifi-picker.py/bluetooth-picker.py:
# Sky for a real, inspectable thing (a running container), Peach for a
# command that changes something mildly (restart -- comes back on its
# own), Red for one that's more final (stop -- stays stopped until someone
# acts again). Not reusing bluetooth-picker.py's exact three-color set
# unchanged here: stop and restart are both "command" in that scheme, but
# have a real severity difference worth signaling separately.
COLOR_INFO = "#89DCEB"     # Sky
COLOR_RESTART = "#FAB387"  # Peach
COLOR_STOP = "#F38BA8"     # Red
COLOR_COMMAND = "#94E2D5"  # Teal -- Stats/Stop All, the two top-level shortcuts


def run(*args, timeout=10):
    try:
        return subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(e.cmd, returncode=1, stdout=e.stdout or "", stderr="timed out")


def notify(message, urgency="low"):
    # Was "utilities-terminal" for the non-critical case -- a generic
    # terminal glyph with no connection to Docker at all, reported
    # directly: "if the notification is about docker then it only has
    # the docker name in it not the icon of it". candy-icons (Papirus's
    # replacement) also ships a real docker-desktop icon under the same
    # name -- confirmed it still resolves via the same GTK icon theme
    # lookup every other themed icon on this system goes through, not
    # assumed from the filename alone (a bare "docker" name doesn't
    # resolve to anything in this theme, "docker-desktop" does).
    # candy-icons has no dialog-error icon at all though (confirmed with
    # `find` -- see mako/config for the full story), so the critical case
    # falls back to AdwaitaLegacy's real red-filled dialog-error.png.
    # docker-desktop is unaffected (real fill, in candy-icons' `apps`
    # category, re-confirmed rendering live via a Docker-blue pixel
    # check after the migration).
    icon = (
        "/usr/share/icons/AdwaitaLegacy/48x48/legacy/dialog-error.png"
        if urgency == "critical"
        else "docker-desktop"
    )
    subprocess.run(["notify-send", "-u", urgency, "-i", icon, "Docker", message], check=False)


def markup(text, color):
    return f'<span foreground="{color}">{text}</span>'


def list_running():
    """[(id, name, image, status, ports), ...] -- tab-separated so names/
    images/statuses with spaces in them can't be mistaken for field
    boundaries the way a plain space-split would risk."""
    out = run("ps", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}").stdout
    containers = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 5:
            containers.append(tuple(parts))
    return containers


def build_menu():
    entries = []
    containers = list_running()

    if not containers:
        entries.append((markup("No containers running", COLOR_INFO), lambda: None))
    else:
        for cid, name, image, status, ports in containers:
            info = f"  {name}  --  {image}  --  {status}"
            if ports:
                info += f"  --  {ports}"
            entries.append((markup(info, COLOR_INFO), (lambda n=name, i=info: show_details(n, i))))
            entries.append((markup(f"  └─   Restart {name}", COLOR_RESTART), (lambda c=cid, n=name: restart_container(c, n))))
            entries.append((markup(f"  └─   Stop {name}", COLOR_STOP), (lambda c=cid, n=name: stop_container(c, n))))

    entries.append((markup("Open docker stats", COLOR_COMMAND), open_stats))
    entries.append((markup("Stop all containers", COLOR_COMMAND), stop_all))
    return entries


def show_details(name, info):
    notify(info.strip())


def restart_container(cid, name):
    notify(f"Restarting {name}...")
    result = run("restart", cid, timeout=30)
    if result.returncode == 0:
        notify(f"Restarted {name}")
    else:
        notify(f"Failed to restart {name}: {result.stderr.strip()}", urgency="critical")


def stop_container(cid, name):
    notify(f"Stopping {name}...")
    result = run("stop", cid, timeout=15)
    if result.returncode == 0:
        notify(f"Stopped {name}")
    else:
        notify(f"Failed to stop {name}: {result.stderr.strip()}", urgency="critical")


def stop_all():
    containers = list_running()
    if not containers:
        notify("No containers were running")
        return
    ids = [c[0] for c in containers]
    result = run("stop", *ids, timeout=30)
    if result.returncode == 0:
        notify(f"Stopped {len(ids)} container(s)")
    else:
        notify(f"Failed to stop all containers: {result.stderr.strip()}", urgency="critical")


def open_stats():
    subprocess.Popen(["kitty", "-e", "docker", "stats"], start_new_session=True)


def get_selection(entries):
    labels = [label for label, _ in entries]
    proc = subprocess.run(
        ["wofi", "--dmenu", "-m", "-p", f"{WOFI_PROMPT} "],
        input="\n".join(labels),
        capture_output=True,
        text=True,
        check=False,
    )
    sel = proc.stdout.strip()
    if not sel:
        sys.exit()
    matches = [action for label, action in entries if label.strip() == sel]
    if len(matches) != 1:
        matches = [action for label, action in entries if sel in label]
    if len(matches) != 1:
        notify("Selection was ambiguous, nothing done", urgency="critical")
        sys.exit(1)
    return matches[0]


def main():
    entries = build_menu()
    action = get_selection(entries)
    action()


if __name__ == "__main__":
    main()
