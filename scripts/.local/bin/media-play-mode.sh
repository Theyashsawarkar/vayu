#!/usr/bin/env bash
# Toggles the playback mode music-search.py uses when Mod+Shift+Y plays
# a search result: "audio" (mpv with no video output, just sound) or
# "video" (mpv with a real window). Same persisted-state pattern as
# notification-mode.sh/theme-toggle.sh -- a plain state file, not
# anything transient, since this needs to be readable by a completely
# separate process (music-search.py) whenever it next runs, not just
# remembered for the lifetime of whatever's running right now.
#
# Usage: media-play-mode.sh audio|video|toggle
set -uo pipefail

STATE_DIR="$HOME/.local/state/media-play-mode"
STATE_FILE="$STATE_DIR/current"
mkdir -p "$STATE_DIR"

current=$(cat "$STATE_FILE" 2>/dev/null || true)
case "$current" in
    audio|video) ;;
    *) current="audio" ;;
esac

case "${1:-toggle}" in
    audio|video)
        new="$1"
        ;;
    toggle)
        if [ "$current" = "audio" ]; then new="video"; else new="audio"; fi
        ;;
    *)
        echo "usage: media-play-mode.sh audio|video|toggle" >&2
        exit 1
        ;;
esac

echo "$new" > "$STATE_FILE"

# Absolute paths, not theme names -- same reasoning as every other icon
# in this repo (mako has no GTK-style theme resolution); confirmed
# present under Papirus's real-fill `devices` category before use.
if [ "$new" = "audio" ]; then
    icon="/usr/share/icons/Papirus/48x48/devices/audio-headphones.svg"
    desc="Mod+Shift+Y now plays search results as audio only"
else
    icon="/usr/share/icons/Papirus/48x48/devices/video-display.svg"
    desc="Mod+Shift+Y now plays search results as video"
fi

notify-send -u normal -i "$icon" "YouTube search: ${new^} mode" "$desc"
