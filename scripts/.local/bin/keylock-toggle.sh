#!/usr/bin/env bash
# Toggles capslock/numlock by injecting a real key press+release via
# ydotool. Takes "capslock" or "numlock" as $1.
#
# Why ydotool and not a Wayland-native tool: tried wtype first (already
# used elsewhere in this repo for the OSD scroll-flood stress test) --
# `wtype -k Caps_Lock` does NOT actually toggle the real lock state here,
# confirmed by checking /sys/class/leds/*::capslock/brightness stayed 0
# through it. wtype injects through the virtual-keyboard-unstable-v1
# Wayland protocol, which this compositor apparently doesn't run through
# the same XKB lock-latch state machine a real key event does. ydotool
# injects through /dev/uinput instead -- a genuine kernel-level virtual
# input device, indistinguishable from real hardware to the same
# libinput -> xkbcommon pipeline that processes actual keypresses, so it
# correctly drives the real lock state.
#
# Requires ydotoold running (systemd --user service, ships with the
# ydotool package) -- checked before attempting the toggle rather than
# failing silently or with a cryptic ydotool error.
set -uo pipefail

KEY="${1:?usage: keylock-toggle.sh capslock|numlock}"

case "$KEY" in
    capslock) KEYCODE=58; LABEL="Caps Lock" ;;
    numlock)  KEYCODE=69; LABEL="Num Lock" ;;
    *) echo "unknown key: $KEY" >&2; exit 1 ;;
esac

# Absolute path, not a theme name -- mako has no GTK-style theme
# resolution. candy-icons (Papirus's replacement) ships no dialog-error
# icon at all (confirmed with `find` -- see mako/config for the full
# story), so this falls back to AdwaitaLegacy's real red-filled
# dialog-error.png instead.
ICON_ERROR=/usr/share/icons/AdwaitaLegacy/48x48/legacy/dialog-error.png

if ! command -v ydotool >/dev/null 2>&1; then
    notify-send -u critical -i "$ICON_ERROR" "$LABEL" "ydotool isn't installed -- run: sudo pacman -S ydotool"
    exit 1
fi

if ! systemctl --user is-active --quiet ydotool.service; then
    notify-send -u critical -i "$ICON_ERROR" "$LABEL" "ydotoold isn't running -- run: systemctl --user enable --now ydotool.service"
    exit 1
fi

ydotool key "${KEYCODE}:1" "${KEYCODE}:0"
