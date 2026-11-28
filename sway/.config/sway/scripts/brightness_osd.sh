#!/bin/bash
# Brightness OSD helper: applies a brightnessctl delta, then fires a
# progress-bar-style mako notification. Used by both the
# XF86MonBrightness* keybindings and the waybar backlight module's
# on-scroll bindings.
#
# flock-serialized for the same reason as volume_osd.sh: this can fire in
# rapid bursts (touchpad smooth-scroll deltas). brightnessctl already
# clamps at 0-100% on its own (verified: "set 1000%" lands at 100%, not an
# overdrive risk the way pactl's relative volume is), but without the lock
# concurrent calls can still stack out of order and overshoot the expected
# per-tick step before settling.
LOCK="${XDG_RUNTIME_DIR:-/tmp}/brightness_osd.lock"

# Fast path (2026-11-28): one call into Vyom, which knows the backlight's
# level, shows the slider at once and sets it through logind (no process);
# the rest runs only when Vyom isn't running. brightnessctl's "+5%" / "5%-"
# become "+5" / "-5".
case "$1" in
    +[0-9]*%) step="+${1:1:${#1}-2}" ;;
    [0-9]*%-) step="-${1%\%-}" ;;
    *) step= ;;
esac
if [ -n "$step" ] && [ "$(busctl --user --auto-start=no call dev.vayu.Vyom /dev/vayu/Vyom/Osd \
        dev.vayu.Vyom.Osd Step s "brightness $step" 2>/dev/null)" = "b true" ]; then
    exit 0
fi

(
    flock -x 9
    brightnessctl set "$1" >/dev/null
) 9>"$LOCK"

percentage=$(brightnessctl -m | cut -d, -f4 | tr -d '%')

# Real (absolute-path) icon, not a theme name -- mako has no GTK-style
# theme resolution, only ever searches hicolor/pixmaps plus icon-path
# (see mako/config). Papirus used to solve this with a real-fill
# display-brightness.svg; candy-icons (its replacement) has no icon of
# that name at all (confirmed with `find`) -- preferences-desktop-display
# is the closest real concept it does ship, confirmed `grep -c
# currentColor` is 0 before using it, same discipline as everywhere else
# in this repo that swapped in a stand-in icon.
ICON=/usr/share/icons/candy-icons/preferences/scalable/preferences-desktop-display.svg

[ -n "$percentage" ] && notify-send -h string:x-canonical-private-synchronous:sys-notify -u low -h int:value:"$percentage" -i "$ICON" "Brightness" "${percentage}%"
