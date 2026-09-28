#!/usr/bin/env python3
"""Phone picker (KDE Connect) for Super+Shift+o and waybar's phone module.
Same modal approach as bluetooth-picker.py (wofi --dmenu, category colors,
active-device marker): per paired phone -- send a file, send the clipboard,
ring it, ping it, browse its storage, unpair -- plus accepting/refusing an
incoming pair request and pairing with a phone that's reachable but not
paired yet.

Built on kdeconnect-cli for actions and the daemon's D-Bus properties
(busctl) for state, both confirmed against kdeconnect 26.08 on this machine
with a real paired phone. The daemon is the systemd user unit
kdeconnect.service; D-Bus activation is redirected to it
(kdeconnect/.local/share/dbus-1/services/), so calling the CLI while it's
down starts the supervised daemon rather than a stray one.

Every entry reads action + object ("Send file to ...", "Ring ..."), the same
convention as the keybinding search.
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

WOFI_PROMPT = "Phone"
ICON_PHONE = "\U000F011C"  # nf-md-cellphone, same glyph as the waybar module
ICON_FILE = "\U000F0214"   # nf-md-file
BUS = "org.kde.kdeconnect"
DEVICE_IFACE = "org.kde.kdeconnect.device"

# Catppuccin Mocha, the same palette/roles as bluetooth-picker.py.
CATEGORY_COLORS = {
    "device": "#89DCEB",   # Sky -- an action on the connected phone
    "nearby": "#94E2D5",   # Teal -- reachable but not paired / not reachable
    "command": "#FAB387",  # Peach -- refresh/daemon actions
}
ACTIVE_STYLE = 'foreground="#CBA6F7" background="#313244" weight="bold" '
ACTIVE_MARKER = "┃ "

# Where "Send file" looks for recent files to offer.
RECENT_DIRS = ["Downloads", "Pictures", "Pictures/Screenshots", "Videos",
               "Documents", "Desktop"]
RECENT_LIMIT = 40


def notify(message, urgency="low"):
    icon = (
        "/usr/share/icons/AdwaitaLegacy/48x48/legacy/dialog-error.png"
        if urgency == "critical"
        else "/usr/share/icons/candy-icons/apps/scalable/kdeconnect.svg"
    )
    subprocess.run(["notify-send", "-a", "KDE Connect", "-u", urgency, "-i", icon,
                    "Phone", message], check=False)


def cli(*args, timeout=15):
    try:
        return subprocess.run(["kdeconnect-cli", *args], capture_output=True,
                              text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 1, "", "timed out")


def prop(dev_id, name, iface=DEVICE_IFACE, path_suffix=""):
    """One D-Bus property of a device, parsed from busctl's `TYPE VALUE`."""
    try:
        out = subprocess.run(
            ["busctl", "--user", "get-property", BUS,
             f"/modules/kdeconnect/devices/{dev_id}{path_suffix}", iface, name],
            capture_output=True, text=True, timeout=5, check=False).stdout.strip()
    except subprocess.TimeoutExpired:
        return None
    if not out:
        return None
    kind, _, value = out.partition(" ")
    if kind == "b":
        return value == "true"
    if kind == "i":
        return int(value)
    return value.strip('"')


def devices():
    """[(id, name, paired, reachable, peer_requested)] for every known device.
    Asks the daemon over D-Bus (~6 ms) rather than `kdeconnect-cli
    --list-devices`, which blocks ~2 s on network discovery every call and
    was most of the delay before the popup appeared."""
    import json
    out = subprocess.run(
        ["busctl", "--user", "--json=short", "call", BUS, "/modules/kdeconnect",
         "org.kde.kdeconnect.daemon", "devices", "bb", "false", "false"],
        capture_output=True, text=True, timeout=10, check=False).stdout
    try:
        ids = json.loads(out)["data"][0]
    except (ValueError, KeyError, IndexError):
        ids = []
    result = []
    for dev_id in ids:
        name = prop(dev_id, "name") or dev_id
        result.append((dev_id, name, bool(prop(dev_id, "isPaired")),
                       bool(prop(dev_id, "isReachable")),
                       bool(prop(dev_id, "isPairRequestedByPeer"))))
    return result


def battery(dev_id):
    charge = prop(dev_id, "charge", "org.kde.kdeconnect.device.battery", "/battery")
    charging = prop(dev_id, "isCharging", "org.kde.kdeconnect.device.battery", "/battery")
    if charge is None or charge < 0:
        return ""
    return f"  {charge}%" + (" charging" if charging else "")


def markup(text, category=None, active=False):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if active:
        return f"<span {ACTIVE_STYLE}>{ACTIVE_MARKER}{text}</span>"
    color = CATEGORY_COLORS.get(category)
    return f'<span foreground="{color}">{text}</span>' if color else text


def build_menu():
    entries = []
    for dev_id, name, paired, reachable, peer_requested in devices():
        if peer_requested:
            entries.append((markup(f"Accept pairing from {name}", "nearby", active=True),
                            lambda d=dev_id, n=name: accept_pairing(d, n)))
            entries.append((markup(f"Reject pairing from {name}", "nearby"),
                            lambda d=dev_id, n=name: reject_pairing(d, n)))
        elif paired and reachable:
            entries.append((markup(f"{ICON_PHONE}  {name}{battery(dev_id)}", active=True), None))
            entries += [
                (markup(f"Send file to {name}", "device"), lambda d=dev_id, n=name: send_file(d, n)),
                (markup(f"Send clipboard to {name}", "device"), lambda d=dev_id, n=name: send_clipboard(d, n)),
                (markup(f"Browse {name} files", "device"), lambda d=dev_id, n=name: browse(d, n)),
                (markup(f"Ring {name} (find my phone)", "device"), lambda d=dev_id, n=name: ring(d, n)),
                (markup(f"Ping {name}", "device"), lambda d=dev_id, n=name: ping(d, n)),
                (markup(f"Unpair {name}", "device"), lambda d=dev_id, n=name: unpair(d, n)),
            ]
        elif paired:
            entries.append((markup(f"{ICON_PHONE}  {name} (paired, not reachable: "
                                   "open KDE Connect on it, same network)", "nearby"),
                            refresh_and_relaunch))
        elif reachable:
            entries.append((markup(f"Pair with {name}", "nearby"),
                            lambda d=dev_id, n=name: pair(d, n)))
    entries.append((markup("Reconnect phones (if something stopped working)", "command"), reconnect))
    entries.append((markup("Refresh devices", "command"), refresh_and_relaunch))
    return entries


def reconnect():
    """Re-announces this laptop and re-establishes every link
    (forceOnNetworkChange), for a session that looks connected but no longer
    carries anything -- e.g. the phone app kept a dead connection. The
    daemon itself stays up, so pairing and settings are untouched."""
    subprocess.run(["busctl", "--user", "call", BUS, "/modules/kdeconnect",
                    "org.kde.kdeconnect.daemon", "forceOnNetworkChange"],
                   capture_output=True, check=False)
    cli("--refresh")
    notify("Reconnecting: if the phone doesn't come back in a few seconds, "
           "open KDE Connect on it")


def pick(labels, prompt):
    proc = subprocess.run(["wofi", "--dmenu", "-m", "-i", "-p", prompt],
                          input="\n".join(labels), capture_output=True, text=True, check=False)
    return proc.stdout.strip()


def recent_files():
    home = Path.home()
    files = []
    for d in RECENT_DIRS:
        p = home / d
        if p.is_dir():
            files += [f for f in p.iterdir() if f.is_file() and not f.name.startswith(".")]
    files = sorted(set(files), key=lambda f: f.stat().st_mtime, reverse=True)
    return files[:RECENT_LIMIT]


def send_file(dev_id, name):
    files = recent_files()
    if not files:
        notify("No recent files in ~/Downloads, ~/Pictures, ~/Documents...", "critical")
        return
    home = str(Path.home())
    labels = [f"{ICON_FILE}  {f.name}   ({str(f.parent).replace(home, '~')})" for f in files]
    sel = pick([markup(l, "device") for l in labels], f"Send to {name} ")
    if not sel:
        return
    plain = sel.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    chosen = next((f for f, l in zip(files, labels) if l in plain), None)
    if chosen is None:
        notify("Couldn't match the selected file", "critical")
        return
    r = cli("-d", dev_id, "--share", str(chosen), timeout=30)
    notify(f"Sent {chosen.name} to {name}" if r.returncode == 0
           else f"Failed to send {chosen.name}: {r.stderr.strip()}",
           "low" if r.returncode == 0 else "critical")


def send_clipboard(dev_id, name):
    """Puts the laptop clipboard on the phone's clipboard (the clipboard
    plugin's sendClipboard), rather than --share-text, which lands on the
    phone as a 'text received' notification instead. Sending is always
    explicit: auto-sync laptop -> phone is off (phone-events.py)."""
    text = subprocess.run(["wl-paste", "--no-newline"], capture_output=True,
                          text=True, check=False).stdout
    if not text:
        notify("Clipboard is empty (or not text)", "critical")
        return
    r = subprocess.run(["busctl", "--user", "call", BUS,
                        f"/modules/kdeconnect/devices/{dev_id}/clipboard",
                        "org.kde.kdeconnect.device.clipboard", "sendClipboard"],
                       capture_output=True, text=True, check=False)
    preview = " ".join(text.split())
    preview = preview if len(preview) <= 60 else preview[:59] + "…"
    notify(f"Sent clipboard to {name}: “{preview}”" if r.returncode == 0
           else f"Failed to send clipboard: {r.stderr.strip()}",
           "low" if r.returncode == 0 else "critical")


def browse(dev_id, name):
    notify(f"Mounting {name} storage...")
    cli("-d", dev_id, "--mount", timeout=20)
    mount = ""
    for _ in range(20):  # the mount appears asynchronously
        mount = cli("-d", dev_id, "--get-mount-point").stdout.strip()
        if mount and os.path.ismount(mount):
            break
        time.sleep(0.5)
    if not (mount and os.path.ismount(mount)):
        notify(f"Couldn't mount {name}: allow storage access in the phone's KDE Connect "
               "app (Filesystem expose / permissions)", "critical")
        return
    # Android never lets the mount root itself be listed ("Permission
    # denied"); the daemon reports which folders the phone exposes (e.g.
    # .../storage/emulated/0 = "Internal shared storage"), so open those.
    dirs = exposed_dirs(dev_id)
    target = mount
    if len(dirs) == 1:
        target = dirs[0][0]
    elif dirs:
        sel = pick([markup(label, "device") for _, label in dirs], f"Browse {name} ")
        target = next((p for p, label in dirs if label in sel), None) if sel else None
        if not target:
            return
    # yazi in its own kitty window: `kitty -e` bypasses kitty.conf's
    # `shell tmux new-session -A -s main`, which would otherwise just attach
    # tmux and ignore the folder (so would xdg-open -> kitty +open here).
    if shutil.which("yazi"):
        subprocess.Popen(["kitty", "--title", f"{name} files", "-e", "yazi", target],
                         start_new_session=True)
    else:
        subprocess.Popen(["xdg-open", target], start_new_session=True)


def exposed_dirs(dev_id):
    """[(path, label)] from the sftp plugin's getDirectories (a{sv})."""
    import json
    out = subprocess.run(
        ["busctl", "--user", "--json=short", "call", BUS,
         f"/modules/kdeconnect/devices/{dev_id}/sftp", "org.kde.kdeconnect.device.sftp",
         "getDirectories"], capture_output=True, text=True, timeout=10, check=False).stdout
    try:
        data = json.loads(out)["data"][0]
    except (ValueError, KeyError, IndexError):
        return []
    return [(path, v.get("data", path)) for path, v in data.items() if os.path.isdir(path)]


def ring(dev_id, name):
    r = cli("-d", dev_id, "--ring")
    notify(f"Ringing {name}" if r.returncode == 0 else f"Failed to ring {name}",
           "low" if r.returncode == 0 else "critical")


def ping(dev_id, name):
    r = cli("-d", dev_id, "--ping-msg", f"Ping from {os.uname().nodename}")
    notify(f"Pinged {name}" if r.returncode == 0 else f"Failed to ping {name}",
           "low" if r.returncode == 0 else "critical")


def pair(dev_id, name):
    cli("-d", dev_id, "--pair")
    notify(f"Pair requested: accept it on {name}")
    enforce_device_policy()


def enforce_device_policy():
    """Newly paired phones get phone-events.py's DEVICE_POLICY."""
    subprocess.Popen(["sh", "-c", "sleep 15; exec ~/.local/bin/phone-events.py "
                      "--enforce-device-policy"], start_new_session=True)


def unpair(dev_id, name):
    cli("-d", dev_id, "--unpair")
    notify(f"Unpaired {name}")


def dbus_call(dev_id, method):
    subprocess.run(["busctl", "--user", "call", BUS, f"/modules/kdeconnect/devices/{dev_id}",
                    DEVICE_IFACE, method], capture_output=True, check=False, timeout=5)


def accept_pairing(dev_id, name):
    dbus_call(dev_id, "acceptPairing")
    notify(f"Paired with {name}")
    enforce_device_policy()


def reject_pairing(dev_id, name):
    dbus_call(dev_id, "cancelPairing")
    notify(f"Rejected pairing from {name}")


def refresh_and_relaunch():
    cli("--refresh")
    time.sleep(2)
    subprocess.Popen([sys.executable, __file__], start_new_session=True)


def main():
    entries = build_menu()
    sel = pick([label for label, _ in entries], f"{WOFI_PROMPT} ")
    if not sel:
        return
    matches = [a for label, a in entries if label.strip() == sel]
    if len(matches) != 1:
        matches = [a for label, a in entries if sel in label]
    if len(matches) != 1:
        notify("Selection was ambiguous, nothing done", "critical")
        sys.exit(1)
    if matches[0] is None:  # the device header row: just reopen
        subprocess.Popen([sys.executable, __file__], start_new_session=True)
        return
    matches[0]()


if __name__ == "__main__":
    main()
