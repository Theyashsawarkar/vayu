#!/usr/bin/env bash
# Switches between this desktop's three notification modes -- normal
# (popup + sound), silent (popup, no sound), dnd (no popup, no sound,
# still recorded to history). The actual behavior for each lives in
# mako/.config/mako/config's [mode=silent]/[mode=dnd] sections; "normal"
# is deliberately just a plain custom mode name with no [mode=normal]
# section of its own -- verified live that an undefined mode name is a
# clean no-op (every global setting applies unchanged), rather than
# relying on mako's own built-in "default" mode, which its own docs flag
# as deprecated and slated for removal.
#
# Usage: notification-mode.sh normal|silent|dnd|next|prev
#   normal/silent/dnd -- jump straight to that mode (sway keybindings)
#   next/prev          -- cycle through the fixed order below (waybar
#                          scroll on the custom/notifications module)
#
# State persisted to a file rather than trusted from `makoctl mode`
# alone: confirmed directly that mako's own mode selection resets to
# "default" on every mako restart (a real, non-obvious gap -- caught
# while testing this, not assumed), which would otherwise silently lose
# whatever the user had actually chosen. See notification-mode-restore.sh
# (run right after `exec mako` in sway/config, same pattern already used
# for swayidle-startup.sh/caffeine mode) for how this gets reapplied.
set -uo pipefail

MODES=(normal silent dnd)
STATE_DIR="$HOME/.local/state/notification-mode"
STATE_FILE="$STATE_DIR/current"
mkdir -p "$STATE_DIR"

current=$(cat "$STATE_FILE" 2>/dev/null || true)
case "$current" in
    normal|silent|dnd) ;;
    *) current="normal" ;;
esac

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
        idx=$(find_index "$current")
        new="${MODES[$(((idx + 1) % ${#MODES[@]}))]}"
        ;;
    prev)
        idx=$(find_index "$current")
        new="${MODES[$(((idx - 1 + ${#MODES[@]}) % ${#MODES[@]}))]}"
        ;;
    *)
        echo "usage: notification-mode.sh normal|silent|dnd|next|prev" >&2
        exit 1
        ;;
esac

echo "$new" > "$STATE_FILE"
makoctl mode -s "$new"

# Absolute paths, not theme names -- mako has no GTK-style theme
# resolution (see brightness_osd.sh / mako/config for the full story).
# candy-icons (Papirus's replacement) ships real-fill versions of all
# three under the same names.
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
        desc="No popups, no sound -- still saved to history"
        ;;
esac

# This notification itself follows whatever mode it just switched into --
# deliberate, not an oversight: if dnd means no popups, the mode-change
# confirmation shouldn't be a carve-out exception to that, and it's still
# in history either way. The waybar bell icon (updated instantly below,
# not left to its own 5s poll interval) is the confirmation that's
# actually guaranteed visible regardless of which mode was just chosen.
notify-send -u normal -i "$icon" "Notifications: $label" "$desc"

# Instant waybar refresh via its "signal" mechanism (custom/notifications'
# own config sets "signal": 8) rather than waiting up to 5s for the next
# poll -- the whole point of this being "soft and flawless" is the icon
# changing the moment you act, not on a delay.
pkill -RTMIN+8 waybar 2>/dev/null || true
