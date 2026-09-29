#!/usr/bin/env bash
# Reports the running-container count for waybar as JSON (same pattern as
# caffeine-status.sh). Icon and count are colored independently via inline
# Pango spans -- icon stays a constant Blue identity color, count switches
# Green/gray depending on whether anything is actually running, so the
# "class" field still drives a border-color tint on the pill itself
# (see style.css) without duplicating that same signal in the text color.

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

# Count is always white (Catppuccin's Text color, not pure #FFFFFF --
# stays consistent with the rest of the theme). running/idle is still
# signaled, just via the pill's border-color now instead of the text.
text="<span color='#89B4FA'>$ICON</span>  <span color='#CDD6F4'>$count</span>"
printf '{"text":"%s","class":"%s","tooltip":"%s"}\n' "$text" "$class" "$tooltip"
