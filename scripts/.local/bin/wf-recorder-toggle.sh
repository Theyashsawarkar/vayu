#!/bin/bash
# =============================================================================
# wf-recorder toggle — start or stop recording
# Usage:
#   wf-recorder-toggle.sh full      → records entire screen
#   wf-recorder-toggle.sh region    → prompts to select a region first
# Output lands in ~/Videos/recordings/ with a timestamp filename.
# =============================================================================

MODE="${1:-full}"
RECORDINGS_DIR="$HOME/Videos/recordings"
PIDFILE="/tmp/wf-recorder.pid"

mkdir -p "$RECORDINGS_DIR"

# Absolute paths, not theme names -- mako has no GTK-style theme
# resolution (see brightness_osd.sh / mako/config for the full story).
# Neither media-record, process-stop, nor audio-input-microphone exists
# in candy-icons (confirmed with `find`) -- microphone-sensitivity-high
# (real fill, `status` category) stands in for "recording" instead, same
# reasoning as before: a microphone reads as close enough to the concept.
# dialog-warning (AdwaitaLegacy, real amber fill -- candy-icons ships no
# dialog-* icons at all) stands in for "cancelled", same reasoning as
# screenshot.sh.
ICON_RECORD=/usr/share/icons/candy-icons/status/scalable/microphone-sensitivity-high.svg
ICON_CANCELLED=/usr/share/icons/AdwaitaLegacy/48x48/legacy/dialog-warning.png

# --- Stop if already recording ---
if [[ -f "$PIDFILE" ]]; then
  pid=$(cat "$PIDFILE")
  if kill -0 "$pid" 2>/dev/null; then
    kill -SIGINT "$pid"
    rm -f "$PIDFILE"
    notify-send -i "$ICON_RECORD" -u low "Recording stopped" "Saved to $RECORDINGS_DIR"
    exit 0
  else
    # Stale pid file
    rm -f "$PIDFILE"
  fi
fi

# --- Start recording ---
OUTFILE="$RECORDINGS_DIR/$(date +%Y%m%d_%H%M%S).mp4"

if [[ "$MODE" == "region" ]]; then
  GEOMETRY=$(slurp 2>/dev/null)
  if [[ -z "$GEOMETRY" ]]; then
    notify-send -u low -i "$ICON_CANCELLED" "Recording cancelled"
    exit 0
  fi
  wf-recorder --geometry "$GEOMETRY" -f "$OUTFILE" &
else
  wf-recorder -f "$OUTFILE" &
fi

echo $! >"$PIDFILE"
notify-send -i "$ICON_RECORD" -u low "Recording started" "$OUTFILE"
