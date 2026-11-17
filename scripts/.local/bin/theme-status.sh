#!/usr/bin/env bash
# Reports current light/dark mode for waybar (see theme-toggle.sh). Reads
# dconf directly rather than a separate state file -- dconf already
# persists on its own across reboots, unlike swayidle's jyoti
# state (which needs one, since that service itself gets reset on every
# login regardless of what was chosen before); a second copy of the same
# state here would just be one more thing that could drift from the
# truth for no reason.

ICON_DARK=''   # fa-moon
ICON_LIGHT=''  # fa-sun

scheme=$(dconf read /org/gnome/desktop/interface/color-scheme 2>/dev/null | tr -d "'")

if [ "$scheme" = "prefer-light" ]; then
    printf '{"text":"%b","class":"light","tooltip":"Light mode -- click to switch to dark"}\n' "$ICON_LIGHT"
else
    printf '{"text":"%b","class":"dark","tooltip":"Dark mode -- click to switch to light"}\n' "$ICON_DARK"
fi
