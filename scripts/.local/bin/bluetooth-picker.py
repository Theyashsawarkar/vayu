#!/usr/bin/env python3
"""Bluetooth picker for waybar's bluetooth module. Same modal approach as
wifi-picker.py (wofi --dmenu, category colors, active-connection marker)
but with Bluetooth's own unique options -- paired devices, connect/
disconnect, scan for nearby devices, power toggle -- and deliberately no
WiFi-specific actions, mirroring wifi-picker.py's exclusion the other way.

Self-contained, built directly on bluetoothctl rather than wrapping an
existing tool: checked first, and the only wofi/dmenu-adjacent Bluetooth
picker that exists is a 3-year-stale rofi-specific AUR package
(rofi-bluetooth-git) -- not worth depending on over a small direct script,
especially since bluetoothctl already has everything needed (confirmed via
`bluetoothctl --help` and `bluetoothctl devices Paired/Connected` on this
machine: bluez 5.87, real paired device tested against).
"""
import re
import subprocess
import sys

WOFI_PROMPT = "Bluetooth"
ICON_DEVICE = ""  # same Bluetooth glyph the waybar module itself uses

# Catppuccin Mocha, matching wifi-picker.py's palette so both menus read as
# one system: Sky for a connectable entity, Teal for "known but passive",
# Peach for a command that changes something.
CATEGORY_COLORS = {
    "device": "#89DCEB",   # Sky -- a paired device, ready to connect
    "nearby": "#94E2D5",   # Teal -- discovered but not paired yet
    "command": "#FAB387",  # Peach -- power/scan/manager actions
}
ACTIVE_STYLE = 'foreground="#CBA6F7" background="#313244" weight="bold" '
# Same border stand-in as wifi-picker.py -- Pango <span> has no border
# attribute at all, this is the closest honest approximation.
ACTIVE_MARKER = "┃ "


def run(*args, timeout=10):
    """bluetoothctl commands that expect a device response (connect,
    disconnect, pair) can hang past their timeout waiting on something
    that will never come back (e.g. a device needing interactive PIN
    confirmation, which has nowhere to go in this flow) -- caught here
    once, centrally, rather than needing a try/except at every call site.
    Callers just see returncode != 0, same as any other failure."""
    try:
        return subprocess.run(
            ["bluetoothctl", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(
            e.cmd, returncode=1, stdout=e.stdout or "", stderr="timed out"
        )


def notify(message, urgency="low"):
    # Icon follows urgency rather than being static -- this repo's own
    # convention elsewhere (mako's [urgency=high] border override, the
    # battery/lock waybar states) of using urgency as the actual signal,
    # not just a mako-internal detail.
    #
    # Absolute paths, not theme names -- mako has no GTK-style theme
    # resolution (see brightness_osd.sh / mako/config for the full story).
    # candy-icons (Papirus's replacement) ships no dialog-error or
    # bluetooth-active icon under those exact names (confirmed with
    # `find`) -- AdwaitaLegacy's real-fill dialog-error.png covers the
    # first, and candy-icons' own network-bluetooth-activated.svg (real
    # fill, active state) is the closest real equivalent for the second.
    icon = (
        "/usr/share/icons/AdwaitaLegacy/48x48/legacy/dialog-error.png"
        if urgency == "critical"
        else "/usr/share/icons/candy-icons/status/scalable/network-bluetooth-activated.svg"
    )
    subprocess.run(
        ["notify-send", "-u", urgency, "-i", icon, "Bluetooth", message],
        check=False,
    )


def is_powered():
    out = run("show").stdout
    return "Powered: yes" in out


def list_devices(filter_name=None):
    """Parse `bluetoothctl devices [filter]` -> [(mac, name), ...]. Filter
    is optional -- bare `devices` (confirmed working: `bluetoothctl
    devices` on this machine) returns every device bluez currently knows
    about, paired or not, which is what surfaces newly-scanned nearby
    devices."""
    args = ["devices"] if filter_name is None else ["devices", filter_name]
    out = run(*args).stdout
    devices = []
    for line in out.splitlines():
        m = re.match(r"Device (\S+) (.+)", line.strip())
        if m:
            devices.append((m.group(1), m.group(2)))
    return devices


def markup(text, category=None, active=False):
    if active:
        return f"<span {ACTIVE_STYLE}>" + ACTIVE_MARKER + text + "</span>"
    color = CATEGORY_COLORS.get(category)
    if color:
        return f'<span foreground="{color}" >' + text + "</span>"
    return text


def build_menu():
    """Returns [(markup_label, zero-arg callable), ...]. Matched back by
    label text after wofi returns a selection -- no need for the
    Action-object indirection wifi-picker.py uses, since there's no
    upstream get_selection() matching logic to stay in sync with here,
    this script owns both sides of the match."""
    entries = []

    if not is_powered():
        # Was a hardcoded "#FAB387" span here, duplicating CATEGORY_COLORS
        # instead of reading from it -- happened to be the same value,
        # but a second copy of a color this repo already keeps one source
        # of truth for is exactly the kind of thing that quietly drifts
        # out of sync if the palette ever changes (the same class of bug
        # documented for the TPM plugin-path split in ARCHITECTURE.md).
        entries.append((markup("Enable Bluetooth", "command"), enable_bluetooth))
        return entries

    entries.append((markup("Disable Bluetooth", "command"), disable_bluetooth))
    entries.append((markup("Scan for Devices", "command"), scan_and_relaunch))
    entries.append((markup("Open Bluetooth Manager", "command"), launch_manager))

    connected_macs = {mac for mac, _ in list_devices("Connected")}
    paired = list_devices("Paired")
    paired_macs = {mac for mac, _ in paired}
    for mac, name in paired:
        label = f"{ICON_DEVICE}  {name}"
        is_conn = mac in connected_macs
        entries.append(
            (
                markup(label, "device", active=is_conn),
                (lambda m=mac, n=name, c=is_conn: disconnect_device(m, n) if c else connect_device(m, n)),
            )
        )

    # Anything bluez currently knows about that isn't already paired --
    # populated by a scan (see scan_and_relaunch). Without this, "Scan for
    # Devices" would run a scan and then show nothing new to act on.
    for mac, name in list_devices():
        if mac in paired_macs:
            continue
        label = f"{ICON_DEVICE}  {name}"
        entries.append((markup(label, "nearby"), (lambda m=mac, n=name: pair_and_connect(m, n))))

    return entries


def enable_bluetooth():
    run("power", "on")
    notify("Bluetooth enabled")
    relaunch()


def disable_bluetooth():
    run("power", "off")
    notify("Bluetooth disabled")


def connect_device(mac, name):
    notify(f"Connecting to {name}...")
    result = run("connect", mac, timeout=15)
    if result.returncode == 0 and "Connection successful" in result.stdout:
        notify(f"Connected to {name}")
    else:
        notify(f"Failed to connect to {name}", urgency="critical")


def disconnect_device(mac, name):
    result = run("disconnect", mac, timeout=10)
    if result.returncode == 0:
        notify(f"Disconnected from {name}")
    else:
        notify(f"Failed to disconnect from {name}", urgency="critical")


def pair_and_connect(mac, name):
    """For a nearby device bluez has seen but never paired with. Bounded
    timeout since this can hang waiting for interactive PIN confirmation
    on devices that need one -- most consumer audio/BLE gear uses
    passkey-less "just works" pairing and completes well within this, but
    a device that genuinely needs a PIN prompt will just time out here
    rather than hang the picker indefinitely (there's nowhere for a PIN
    prompt to go in this flow -- a real, documented limitation, not
    silently papered over)."""
    notify(f"Pairing with {name}...")
    pair_result = run("pair", mac, timeout=20)
    if pair_result.returncode != 0 or "Failed" in pair_result.stdout:
        notify(f"Failed to pair with {name} (may need a PIN -- try Bluetooth Manager instead)", urgency="critical")
        return
    run("trust", mac, timeout=5)
    connect_device(mac, name)


def scan_and_relaunch():
    notify("Scanning for nearby devices (8s)...")
    try:
        subprocess.run(
            ["bluetoothctl", "--timeout", "8", "scan", "on"],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pass
    relaunch()


def launch_manager():
    subprocess.Popen(["blueman-manager"], start_new_session=True)


def relaunch():
    """Re-invoke this same script so a state change (power toggled, scan
    just ran) shows up in a fresh menu -- same pattern
    networkmanager_dmenu itself uses after a rescan (calls main() again)."""
    subprocess.Popen([sys.executable, __file__], start_new_session=True)


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
        # Fall back to a loose match in case wofi trims/alters whitespace
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
