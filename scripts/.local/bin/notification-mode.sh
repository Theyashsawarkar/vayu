#!/usr/bin/env bash
# Switches between this desktop's three notification modes: normal (popup
# + sound), silent (popup, no sound), dnd (no popup except urgent ones, no
# sound, still kept in the history). They're akashvani's modes (the
# notification server, inside Vyom): it remembers the mode across restarts
# and reboots, so nothing has to reapply it at login. akashvani's panel
# adds its own "do-not-disturb" mode for a timed do not disturb; it counts
# as dnd here.
#
# Usage: notification-mode.sh normal|silent|dnd|next|prev
#   normal/silent/dnd -- jump straight to that mode (sway keybindings)
#   next/prev          -- cycle through the fixed order below (waybar
#                          scroll on the custom/notifications module)
set -uo pipefail

MODES=(normal silent dnd)
# The state file is only a copy for anything that reads it; akashvani's
# modes are the truth.
STATE_DIR="$HOME/.local/state/notification-mode"
STATE_FILE="$STATE_DIR/current"
mkdir -p "$STATE_DIR"

current() {
    local m
    m=$(akashvani mode 2>/dev/null)
    case $'\n'"$m"$'\n' in
        *$'\n'dnd$'\n'*|*$'\n'do-not-disturb$'\n'*) echo dnd ;;
        *$'\n'silent$'\n'*) echo silent ;;
        *) echo normal ;;
    esac
}

find_index() {
    local target="$1" i
    for i in "${!MODES[@]}"; do
        [ "${MODES[$i]}" = "$target" ] && echo "$i" && return
    done
    echo 0
}

case "${1:-}" in
    normal|silent|dnd)
        new="$1"
        ;;
    next)
        idx=$(find_index "$(current)")
        new="${MODES[$(((idx + 1) % ${#MODES[@]}))]}"
        ;;
    prev)
        idx=$(find_index "$(current)")
        new="${MODES[$(((idx - 1 + ${#MODES[@]}) % ${#MODES[@]}))]}"
        ;;
    *)
        echo "usage: notification-mode.sh normal|silent|dnd|next|prev" >&2
        exit 1
        ;;
esac

echo "$new" > "$STATE_FILE"
# -s replaces every mode, so a timed do not disturb from the panel ends too
akashvani mode -s "$new" >/dev/null

case "$new" in
    normal)
        icon="/usr/share/icons/candy-icons/preferences/scalable/preferences-system-notifications.svg"
        label="Normal"
        desc="Popups and sound for every notification"
        ;;
    silent)
        icon="/usr/share/icons/candy-icons/status/scalable/audio-volume-muted.svg"
        label="Silent"
        desc="Popups still show, sound is off"
        ;;
    dnd)
        icon="/usr/share/icons/candy-icons/status/scalable/notification-disabled.svg"
        label="Do Not Disturb"
        desc="No popups (urgent ones still show), no sound -- still saved to history"
        ;;
esac

# shows even when switching into dnd: a rule in vyom/config.toml (show_in_dnd)
notify-send -a akashvani -t 3000 \
    -h string:x-canonical-private-synchronous:notification-mode -i "$icon" "Notifications: $label" "$desc"

"$HOME/.local/bin/waybar-signal" 8 2>/dev/null || true
