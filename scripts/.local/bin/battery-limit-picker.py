#!/usr/bin/env python3
"""Battery charge-limit reminder picker for waybar's battery module.

A software-only reminder, deliberately NOT a hardware charge cutoff:
this laptop (Acer Aspire A315-23) has no charge_control_end_threshold
under /sys/class/power_supply/BAT1 -- confirmed directly, the firmware
doesn't expose one to Linux at all. The only real workaround, a
community acer-wmi-battery kernel module, is untested on this exact
model (its own MODELS.md lists several other A315 variants working/not
working, A315-23 isn't in either list) and only offers a fixed 80%
on/off toggle anyway, not a real range. Acer's own Community forum also
has a report from another A315-23 owner whose laptop wouldn't boot with
the charger plugged in after enabling the equivalent feature in Acer's
OWN official Windows software (Care Center) -- a strong signal this
model's EC handling of hardware charge-limiting is unreliable
regardless of OS, not worth the risk of touching real EC/firmware
state for a "nice to have".

So: this just picks a target percentage and writes it to a state file;
battery-limit-watch.sh (a plain udevadm-driven watcher, same pattern as
battery-warning-dismiss.sh) fires a notify-send nudge once per charge
session when you cross it, or when you plug in while already above it.
You still decide when to actually unplug. The choice lives in
~/.local/state/battery-limit/threshold, so it survives reboots.
"""
import subprocess
import sys
from pathlib import Path

WOFI_PROMPT = "Battery limit"
STATE_DIR = Path.home() / ".local/state/battery-limit"
STATE_FILE = STATE_DIR / "threshold"
OPTIONS = [90, 80, 75, 70, 60, 50]
SUGGESTED = 70

# Same Catppuccin Mocha convention as the other pickers (docker-picker.py/
# wifi-picker.py/bluetooth-picker.py): Sky for a real selectable option,
# Red for the one that turns things off, Green for "this is active now".
COLOR_CURRENT = "#A6E3A1"
COLOR_OPTION = "#89DCEB"
COLOR_OFF = "#F38BA8"

ICON_DIR = "/usr/share/icons/candy-icons/status/scalable"


def read_current():
    try:
        raw = STATE_FILE.read_text().strip()
    except FileNotFoundError:
        return None
    return int(raw) if raw.isdigit() and 0 < int(raw) <= 100 else None


def markup(text, color):
    return f'<span foreground="{color}">{text}</span>'


def notify(title, message, icon):
    subprocess.run(["notify-send", "-u", "normal", "-i", icon, title, message], check=False)


def build_menu(current):
    entries = []
    off_tag = "  (current)" if current is None else ""
    entries.append((markup(f"Off -- no reminder{off_tag}", COLOR_OFF), lambda: set_limit(None)))
    for pct in OPTIONS:
        tags = []
        if pct == SUGGESTED:
            tags.append("suggested")
        if pct == current:
            tags.append("current")
        suffix = f"  ({', '.join(tags)})" if tags else ""
        color = COLOR_CURRENT if pct == current else COLOR_OPTION
        entries.append((markup(f"{pct}%{suffix}", color), (lambda p=pct: set_limit(p))))
    return entries


def set_limit(pct):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if pct is None:
        STATE_FILE.write_text("off")
        notify("Battery reminder off", "Won't nudge you to unplug anymore.",
               f"{ICON_DIR}/battery-100-charging.svg")
        return
    STATE_FILE.write_text(str(pct))
    bucket = round(pct / 10) * 10
    icon = f"{ICON_DIR}/battery-{bucket:03d}-charging.svg"
    plugged, cap = power_state()
    if plugged and cap is not None and cap >= pct:
        # Already past the new limit while charging: say so now, and tell the
        # watcher (its flag stores the limit it fired for) not to repeat it.
        (STATE_DIR / ".notified").write_text(str(pct))
        notify(
            f"Battery reminder set to {pct}%",
            f"You're at {cap}% and charging -- already past this limit. Unplug when you can.",
            icon,
        )
        return
    notify(
        f"Battery reminder set to {pct}%",
        "You'll get a nudge to unplug once charging crosses this, or if you plug in while already above it.",
        icon,
    )


def power_state():
    """(plugged_in, capacity%) from sysfs, or (False, None) if unreadable."""
    root = Path("/sys/class/power_supply")
    plugged, cap = False, None
    for d in root.glob("*"):
        try:
            kind = (d / "type").read_text().strip()
            if kind == "Battery":
                cap = int((d / "capacity").read_text())
            elif (d / "online").read_text().strip() == "1":
                plugged = True
        except (OSError, ValueError):
            continue
    return plugged, cap


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
        notify("Selection was ambiguous, nothing done", "", f"{ICON_DIR}/battery-good.svg")
        sys.exit(1)
    return matches[0]


def main():
    current = read_current()
    entries = build_menu(current)
    action = get_selection(entries)
    action()


if __name__ == "__main__":
    main()
