#!/usr/bin/env bash
# ExecStartPre for mpd.service (systemd/.config/systemd/user/mpd.service.d):
# creates every directory mpd.conf points at. mpd refuses to start when
# music_directory, playlist_directory or the parent of db_file/state_file/
# sticker_file is missing -- which on a fresh machine they all are. The
# paths are read from mpd.conf itself so this can't drift from it.
set -euo pipefail
conf="${XDG_CONFIG_HOME:-$HOME/.config}/mpd/mpd.conf"
[ -r "$conf" ] || exit 0
sed -nE 's/^[[:space:]]*(music_directory|playlist_directory)[[:space:]]+"([^"]+)".*/\2/p
         s/^[[:space:]]*(db_file|state_file|sticker_file)[[:space:]]+"([^"]+)\/[^/"]+".*/\2/p' "$conf" |
  while IFS= read -r dir; do
    case $dir in "~"*) dir="$HOME${dir#\~}" ;; esac
    mkdir -p "$dir"
  done
