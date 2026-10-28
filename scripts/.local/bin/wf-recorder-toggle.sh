#!/bin/bash
# =============================================================================
# wf-recorder toggle — start or stop recording
# Usage:
#   wf-recorder-toggle.sh full      → records entire screen
#   wf-recorder-toggle.sh region    → prompts to select a region first
# Output lands in ~/Videos/recordings/ with a timestamp filename, with the
# system's sound (what you hear, not the mic). The GPU encodes (VA-API)
# when it can, else the CPU (libx264). Stopping copies the file, ready to
# paste into chat/mail. The bar shows a REC timer meanwhile
# (wf-recorder-status.sh, custom/recording; a click on it stops).
# =============================================================================

MODE="${1:-full}"
RECORDINGS_DIR="$HOME/Videos/recordings"
# In the user's runtime dir (not a shared, guessable /tmp name).
# Lines: pid, output file, start time (epoch seconds).
PIDFILE="${XDG_RUNTIME_DIR:-/tmp}/wf-recorder.pid"
BAR_SIGNAL=16
log() { logger -t wf-recorder-toggle -- "$*"; }

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
  { read -r pid; read -r outfile; } <"$PIDFILE"
  # Only if that pid is still wf-recorder: if it died on its own, the pid
  # may belong to something else by now, which got the SIGINT.
  if [[ "$(cat "/proc/$pid/comm" 2>/dev/null)" == wf-recorder ]]; then
    kill -SIGINT "$pid"
    rm -f "$PIDFILE"
    waybar-signal "$BAR_SIGNAL"
    # Wait for it to finish writing the file (up to 10 s) before handing it out.
    for _ in {1..100}; do
      [[ -e "/proc/$pid" ]] || break
      sleep 0.1
    done
    # As a file (text/uri-list): pastes as an attachment in chat, mail, Files.
    wl-copy -t text/uri-list "file://$outfile"
    notify-send -i "$ICON_RECORD" -u low "Recording saved" "$outfile\nCopied, ready to paste."
    exit 0
  else
    # Stale pid file
    rm -f "$PIDFILE"
    waybar-signal "$BAR_SIGNAL"
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
  where=(--geometry "$GEOMETRY")
else
  # -o: the focused output. Without it, with two monitors wf-recorder asks
  # on stdin which one, and there's no one to answer.
  output=$(swaymsg -t get_outputs 2>/dev/null | jq -r '.[] | select(.focused) | .name' | head -n1)
  where=(${output:+-o "$output"})
fi

# System sound: the default sink's monitor. No sink (no sound server):
# record without sound rather than fail.
audio=()
sink=$(pactl get-default-sink 2>/dev/null) && [[ -n "$sink" ]] && audio=(--audio="$sink.monitor")

# The GPU's encoder: first render node, if VA-API can use it. Detected, not
# assumed: no node, or a GPU/driver without H.264 encode, falls back below.
render=$(ls /dev/dri/renderD* 2>/dev/null | head -n1)

# start <encoder args...>: runs wf-recorder, true if it is still running
# shortly after (it exits at once on a bad encoder, output or audio device).
start() {
  wf-recorder "${where[@]}" "${audio[@]}" "$@" -f "$OUTFILE" </dev/null 2> >(logger -t wf-recorder) &
  pid=$!
  sleep 0.6
  kill -0 "$pid" 2>/dev/null
}

if [[ -n "$render" ]] && start -c h264_vaapi -d "$render"; then
  encoder="GPU"
elif rm -f "$OUTFILE"; start -c libx264 -p preset=veryfast -p crf=23; then
  [[ -n "$render" ]] && log "VA-API encoding failed on $render; recording with libx264 (CPU)"
  encoder="CPU"
else
  log "wf-recorder exited at once (mode $MODE); see: journalctl --user -t wf-recorder"
  notify-send -u critical -i "$ICON_CANCELLED" "Recording failed" "wf-recorder didn't start: journalctl --user -t wf-recorder"
  exit 1
fi
printf '%s\n%s\n%s\n' "$pid" "$OUTFILE" "$(date +%s)" >"$PIDFILE"
waybar-signal "$BAR_SIGNAL"
sound=${audio:+with sound}
notify-send -i "$ICON_RECORD" -u low "Recording started" "${sound:-no sound}, $encoder encoding. Same key (or the bar's REC) stops."
