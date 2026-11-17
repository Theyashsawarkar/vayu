#!/usr/bin/env bash
# Reports the current notification mode + history count for waybar (see
# akashvani, the panel this icon opens on click, and
# notification-mode.sh, what changes the mode this icon reflects).
#
# Asks akashvani (the notification server, inside Vyom) for its modes and
# the history's size in one D-Bus call. busctl + jq, not the `akashvani`
# command: this runs on every closed notification (bar-events.py), and
# starting Python cost ~50 ms a time against a few ms for these. While mako
# still serves notifications (before the switch), it falls back to makoctl.

st=$(busctl --user --json=short call org.freedesktop.Notifications /dev/vayu/Akashvani \
    dev.vayu.Akashvani Status 2>/dev/null | jq -r '.data[0]' 2>/dev/null)
if [ -n "$st" ]; then
    count=$(jq -r '.history' <<<"$st")
    modes=$(jq -r '.modes[]' <<<"$st")
else
    count=$(makoctl history -j 2>/dev/null | jq length 2>/dev/null)
    modes=$(makoctl mode 2>/dev/null)
fi
count="${count:-0}"
case $'\n'"$modes"$'\n' in
    *$'\n'dnd$'\n'*|*$'\n'do-not-disturb$'\n'*) mode=dnd ;;
    *$'\n'silent$'\n'*) mode=silent ;;
    *) mode=normal ;;
esac

# Each mode gets its own bell variant, not just its own color -- asked
# for the icon shape to change again after briefly trying color-only.
# All three stay in the bell family (not e.g. a generic circle/moon)
# so it still reads as "the notification bell" at a glance, just in a
# different state, colors below still doing the rest of the work.
ICON_NORMAL=''  # fa-bell
ICON_SILENT=''  # fa-bell-slash
ICON_DND='󰂠'  # md-bell-sleep -- still a bell, distinct silhouette from bell-slash

case "$mode" in
    normal) icon="$ICON_NORMAL"; label="Normal" ;;
    silent) icon="$ICON_SILENT"; label="Silent" ;;
    dnd)    icon="$ICON_DND";    label="Do Not Disturb" ;;
esac

tooltip="$label -- $count notification(s) in history -- click to view, scroll to change mode"

printf '{"text":"%b","class":"%s","tooltip":"%s"}\n' "$icon" "$mode" "$tooltip"
