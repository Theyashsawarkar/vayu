#!/usr/bin/env bash
# ekatva's capsule for waybar (custom/ekatva) and quick settings' tile: shown
# only while ekatva.service runs (ekatva-toggle.sh), hidden when it's off.
# JSON like jyoti-status.sh. Refreshed on signal 13 by ekatva-toggle.sh
# and bar-events.py (which follows the unit's state), never polled.
ICON=$'\U000f011c'   # nf-md-cellphone_link
if systemctl --user is-active --quiet ekatva.service; then
    printf '{"text":"%s","class":"active","tooltip":"ekatva on: phone linked\\nClick: open ekatva · Right click: turn it off"}\n' "$ICON"
else
    printf '{"text":"","class":"inactive","tooltip":"ekatva off"}\n'
fi
