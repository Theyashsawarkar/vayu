#!/usr/bin/env bash
# Reports the running-container count for waybar as JSON (same pattern as
# caffeine-status.sh). Icon and count are colored independently via inline
# Pango spans -- icon stays a constant Blue identity color, count switches
# Green/gray depending on whether anything is actually running, so the
# "class" field still drives a border-color tint on the pill itself
# (see style.css) without duplicating that same signal in the text color.

# Colours from the current varna theme (palette.json), Vayu's own without it.
PALETTE=${XDG_STATE_HOME:-$HOME/.local/state}/varna/palette.json
col() { local v; v=$(jq -r ".colors.$1 // empty" "$PALETTE" 2>/dev/null); echo "${v:-$2}"; }

ICON=$''
# docker is socket-activated (install.sh), so `docker ps` against a stopped
# daemon would start it -- on every refresh of this capsule. Only ask docker
# once it is actually running.
count=0
systemctl is-active --quiet docker.service && count=$(docker ps -q | wc -l)

if [ "$count" -gt 0 ]; then
    class="running"
    tooltip="$count container(s) running"
else
    class="idle"
    tooltip="No containers running"
fi

# Icon in the theme's accent, count in its text colour. running/idle is still
# signaled, just via the pill's border-color now instead of the text.
text="<span color='$(col accent '#CBA6F7')'>$ICON</span>  <span color='$(col fg '#CDD6F4')'>$count</span>"
# Hidden while nothing runs: an "only while on" indicator on the bar.
[ "$count" -gt 0 ] || text=""
printf '{"text":"%s","class":"%s","tooltip":"%s"}\n' "$text" "$class" "$tooltip"
