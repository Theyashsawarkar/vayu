#!/usr/bin/env bash
# Charge-limit nudges -- a software reminder only, not a hardware charge
# cutoff (this Acer Aspire A315-23 exposes no charge_control_end_threshold;
# see battery-limit-picker.py's docstring and docs/ARCHITECTURE.md).
#
# Reads the percentage battery-limit-picker.py saved (a plain number, or
# "off") and notifies, once per situation, when:
#   1. the charger is PLUGGED IN while the battery is already at/above the
#      limit  -> "charging isn't needed, unplug" (preventive; this is the
#      "boot above the limit, then plug in" case)
#   2. the battery CROSSES the limit while charging -> "limit reached"
#   3. the battery reaches 100% after having been nudged -> "fully charged"
# It stays silent when: the reminder is off; the charger is unplugged; you
# plug in below the limit; or the machine boots/the service starts with the
# charger ALREADY in (only a fresh plug-in event, or a real crossing, nudges).
# Changing the limit re-arms it (the flag file stores the limit it fired for).
#
# Driven by the kernel's power_supply uevents (same udevadm pattern as
# battery-warning-dismiss.sh), plus a 60 s tick so a plug/unplug that happens
# during suspend, or a missed uevent, is still caught after resume.
#
# Test hooks (env): BATTERY_PS_ROOT, BATTERY_STATE_DIR, BATTERY_NOTIFY.
set -uo pipefail

PS_ROOT="${BATTERY_PS_ROOT:-/sys/class/power_supply}"
STATE_DIR="${BATTERY_STATE_DIR:-$HOME/.local/state/battery-limit}"
STATE_FILE="$STATE_DIR/threshold"
NOTIFIED_FLAG="$STATE_DIR/.notified"   # contains the limit it fired for
FULL_FLAG="$STATE_DIR/.full"
NOTIFY="${BATTERY_NOTIFY:-notify-send}"
ICON_DIR=/usr/share/icons/candy-icons/status/scalable
TICK="${BATTERY_TICK:-60}"

prev_plugged=0

capacity() {
    local d
    for d in "$PS_ROOT"/*; do
        [ "$(cat "$d/type" 2>/dev/null)" = "Battery" ] || continue
        cat "$d/capacity" 2>/dev/null && return
    done
    echo 0
}

plugged() {
    local d t
    for d in "$PS_ROOT"/*; do
        t=$(cat "$d/type" 2>/dev/null) || continue
        [ "$t" = "Battery" ] && continue
        [ "$(cat "$d/online" 2>/dev/null)" = "1" ] && { echo 1; return; }
    done
    echo 0
}

threshold() {
    local t
    t=$(cat "$STATE_FILE" 2>/dev/null || true)
    case "$t" in
        ''|*[!0-9]*) return ;;                    # unset / "off" / garbage
    esac
    { [ "$t" -ge 1 ] && [ "$t" -le 100 ]; } && echo "$t"
}

nudge() {  # title body capacity
    local bucket=$(( ($3 / 10) * 10 ))
    [ "$bucket" -gt 100 ] && bucket=100
    "$NOTIFY" -u normal -i "$ICON_DIR/battery-$(printf '%03d' "$bucket")-charging.svg" \
        -h string:x-canonical-private-synchronous:battery-limit "$1" "$2"
}

notified() { [ "$(cat "$NOTIFIED_FLAG" 2>/dev/null)" = "$1" ]; }

evaluate() {
    local now cap thr
    now=$(plugged); cap=$(capacity); thr=$(threshold)

    if [ "$now" != "1" ]; then                     # on battery: reset everything
        rm -f "$NOTIFIED_FLAG" "$FULL_FLAG"
        prev_plugged=0
        return
    fi
    if [ -z "$thr" ]; then                         # reminder off
        rm -f "$NOTIFIED_FLAG" "$FULL_FLAG"
        prev_plugged=1
        return
    fi
    if [ "$cap" -lt "$thr" ]; then                 # below the limit: re-arm
        rm -f "$NOTIFIED_FLAG" "$FULL_FLAG"
        prev_plugged=1
        return
    fi

    if [ "$prev_plugged" != "1" ]; then            # fresh plug-in, already past the limit
        if [ "$cap" -ge 100 ]; then
            nudge "Charger connected -- battery is full" \
                  "Already at 100%, no need to charge. Unplug to protect long-term battery health." "$cap"
            touch "$FULL_FLAG"
        else
            nudge "Charger connected at ${cap}%" \
                  "You're already past your ${thr}% limit, so charging isn't needed. Unplug to protect long-term battery health." "$cap"
        fi
        echo "$thr" > "$NOTIFIED_FLAG"
    elif ! notified "$thr"; then                   # crossed the limit while charging
        nudge "Battery at ${cap}% -- limit reached" \
              "You've hit your ${thr}% charge limit. Unplug now for better long-term battery health." "$cap"
        echo "$thr" > "$NOTIFIED_FLAG"
    fi

    if [ "$cap" -ge 100 ] && [ ! -e "$FULL_FLAG" ]; then   # still plugged all the way to full
        nudge "Battery full (100%)" \
              "Charged well past your ${thr}% limit -- please unplug." "$cap"
        touch "$FULL_FLAG"
    fi
    prev_plugged=1
}

init() {
    mkdir -p "$STATE_DIR"
    rm -f "$NOTIFIED_FLAG" "$FULL_FLAG"
    prev_plugged=$(plugged)
    # Started with the charger already in and past the limit (boot, service
    # restart): stay quiet -- only a fresh plug-in or a real crossing nudges.
    local thr; thr=$(threshold)
    if [ "$prev_plugged" = "1" ] && [ -n "$thr" ] && [ "$(capacity)" -ge "$thr" ]; then
        echo "$thr" > "$NOTIFIED_FLAG"
        [ "$(capacity)" -ge 100 ] && touch "$FULL_FLAG"
    fi
}

main() {
    init
    exec {fd}< <(udevadm monitor --udev --subsystem-match=power_supply 2>/dev/null)
    local line rc
    while true; do
        if read -r -t "$TICK" -u "$fd" line; then
            case "$line" in *change*|*add*|*remove*) ;; *) continue ;; esac
        else
            rc=$?
            [ "$rc" -le 128 ] && exit 1            # udevadm ended -> let systemd restart us
        fi
        evaluate
    done
}

[ "${BASH_SOURCE[0]}" = "$0" ] && main "$@"
