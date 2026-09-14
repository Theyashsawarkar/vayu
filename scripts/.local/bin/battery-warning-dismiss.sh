#!/usr/bin/env bash
# Silently dismisses any currently-shown batsignal notification the
# moment AC power is restored -- the fix for a real, reported problem
# (a low-battery warning stayed on screen after plugging in, needing a
# manual click) without the noise a different fix produced first.
#
# batsignal's own -p flag was tried and reverted: confirmed directly in
# its source that -p fires a "charging" AND a "discharging" announcement
# together (one shared toggle, no way to get just one), so it also fired
# a "Discharging: 40%" toast on every unplug regardless of battery level
# -- unwanted noise, not a warning. This script produces zero
# notifications of its own; it only ever closes one that's already open.
#
# udevadm monitor (not upower --monitor) specifically: its output format
# is small, stable, core-systemd tooling -- not something meant primarily
# for human debugging the way upower's text monitor is documented to be.
# Reacting to the kernel's own power_supply "change" uevent and then
# reading /sys/class/power_supply/ACAD/online directly (the same
# interface batsignal itself polls) means this never depends on upower
# being installed, or on parsing another tool's free-text output.
set -uo pipefail

udevadm monitor --udev --subsystem-match=power_supply | while read -r line; do
    case "$line" in
        *change*ACAD*) ;;
        *) continue ;;
    esac

    online=$(cat /sys/class/power_supply/ACAD/online 2>/dev/null || echo 0)
    [ "$online" = "1" ] || continue

    id=$(makoctl list -j | python3 -c "
import json, sys
for n in json.load(sys.stdin):
    if n.get('app_name') == 'batsignal':
        print(n['id'])
        break
")
    [ -n "$id" ] && makoctl dismiss -n "$id"
done
