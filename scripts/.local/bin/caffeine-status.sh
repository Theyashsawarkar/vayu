#!/usr/bin/env bash
# Reports caffeine-mode state for waybar (see caffeine-toggle.sh). Caffeine
# is "on" precisely when swayidle.service is stopped. JSON output so
# waybar can style the active state distinctly via CSS class.

ICON=$'\uf0f4'

if systemctl --user is-active --quiet swayidle.service; then
    # Hidden when off (quick settings has the toggle); class stays for vyom.
    printf '{"text":"","class":"inactive","tooltip":"Caffeine off"}\n'
else
    printf '{"text":"%s","class":"active","tooltip":"Caffeine on -- click to let the screen sleep again"}\n' "$ICON"
fi
