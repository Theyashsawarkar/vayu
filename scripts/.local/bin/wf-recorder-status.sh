#!/usr/bin/env bash
# Waybar's custom/recording: a REC capsule with the elapsed time while
# wf-recorder-toggle.sh records, hidden otherwise. Runs every second
# (cheap: reads one file, no processes when idle); the toggle also
# signals it (16) so it appears and goes the moment you press the key.

PIDFILE="${XDG_RUNTIME_DIR:-/tmp}/wf-recorder.pid"

{ read -r pid; read -r _; read -r started; } 2>/dev/null <"$PIDFILE"
if [[ -z "$pid" || "$(cat "/proc/$pid/comm" 2>/dev/null)" != wf-recorder ]]; then
    printf '{"text":"","class":"idle"}\n'
    exit 0
fi
secs=$(( $(printf '%(%s)T' -1) - ${started:-0} ))
if (( secs >= 3600 )); then
    elapsed=$(printf '%d:%02d:%02d' $((secs / 3600)) $((secs % 3600 / 60)) $((secs % 60)))
else
    elapsed=$(printf '%02d:%02d' $((secs / 60)) $((secs % 60)))
fi
printf '{"text":"● REC %s","class":"active","tooltip":"Recording -- click to stop and save"}\n' "$elapsed"
