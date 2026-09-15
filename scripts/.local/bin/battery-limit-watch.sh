#!/usr/bin/env bash
# Fires a once-per-charge-session notify-send nudge once the battery
# crosses whatever percentage battery-limit-picker.py last saved (waybar's
# battery module on-click) -- a software reminder only, not a hardware
# charge cutoff. See battery-limit-picker.py's own module docstring and
# docs/ARCHITECTURE.md for exactly why: this laptop (Acer Aspire A315-23)
# has no charge_control_end_threshold, the only Linux kernel workaround is
# untested on this model and fixed at 80% anyway, and Acer's OWN official
# Windows equivalent of this feature has a real reported crash-on-charger
# -plug-in bug on this same model -- not worth the risk of touching real
# EC/firmware state for this.
#
# Same udevadm-monitor pattern as battery-warning-dismiss.sh, reacting to
# the kernel's own power_supply "change" uevents rather than polling on a
# timer -- see that script's own comment for why (small, stable output,
# doesn't depend on upower being installed, reads the same sysfs files
# upower itself would).
set -uo pipefail

STATE_DIR="$HOME/.local/state/battery-limit"
STATE_FILE="$STATE_DIR/threshold"
NOTIFIED_FLAG="$STATE_DIR/.notified"
ICON_DIR=/usr/share/icons/candy-icons/status/scalable
mkdir -p "$STATE_DIR"

udevadm monitor --udev --subsystem-match=power_supply | while read -r line; do
    case "$line" in
        *change*ACAD*|*change*BAT1*) ;;
        *) continue ;;
    esac

    online=$(cat /sys/class/power_supply/ACAD/online 2>/dev/null || echo 0)
    if [ "$online" != "1" ]; then
        # Unplugged -- clear the flag so the next charge session nudges
        # again once it re-crosses the threshold, instead of staying
        # silent forever after the first nudge ever fired.
        rm -f "$NOTIFIED_FLAG"
        continue
    fi

    threshold=$(cat "$STATE_FILE" 2>/dev/null || true)
    case "$threshold" in
        ''|*[!0-9]*) continue ;;  # unset, "off", or garbage -- reminder disabled
    esac

    capacity=$(cat /sys/class/power_supply/BAT1/capacity 2>/dev/null || echo 0)
    if [ "$capacity" -lt "$threshold" ]; then
        rm -f "$NOTIFIED_FLAG"
        continue
    fi

    [ -e "$NOTIFIED_FLAG" ] && continue

    bucket=$(( (capacity / 10) * 10 ))
    [ "$bucket" -gt 100 ] && bucket=100
    icon="$ICON_DIR/battery-$(printf '%03d' "$bucket")-charging.svg"
    notify-send -u normal -i "$icon" "Battery at ${capacity}%" \
        "Past your ${threshold}% charge limit -- unplug soon for better long-term battery health."
    touch "$NOTIFIED_FLAG"
done
