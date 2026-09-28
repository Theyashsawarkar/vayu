#!/usr/bin/env bash
# Centred popup inside the pane area (below/above the status bar).
#   popup.sh <client> <width%> <height%> [display-popup args...] <command>
#
# tmux centres popups on the whole client, status rows included, and
# display-popup's -h doesn't take formats -- so with a 2-row status bar on
# top, big popups got shoved up against the bar and looked cropped.
# Sizes here are a % of the pane area, and -y (the popup's bottom edge)
# is computed so the margin above and below is equal.

c=$1 w=$2 hp=$3; shift 3
read -r ch wh pos < <(tmux display -p -c "$c" '#{client_height} #{window_height} #{status-position}')

h=$(( wh * hp / 100 ))
[ "$pos" = top ] && top=$(( ch - wh )) || top=0
y=$(( top + (wh - h) / 2 + h ))

# Always exit 0: run-shell would otherwise show "returned 130" in a view
# pane whenever the tool inside quits with Esc / Ctrl-c.
tmux display-popup -c "$c" -w "$w%" -h "$h" -x C -y "$y" "$@" || true
