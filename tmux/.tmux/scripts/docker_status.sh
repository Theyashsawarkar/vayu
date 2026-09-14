#!/usr/bin/env bash
# Docker segment for the tmux status bar.
#
# Shows a docker icon + running-container count whenever the docker daemon
# is reachable, even if that count is zero. Prints nothing (hiding the
# segment) if the daemon isn't up, so it doesn't clutter the bar.

icon=$'\uf308' # nf-linux-docker (U+F308)

running=0
if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet docker 2>/dev/null; then
    running=1
elif pgrep -x dockerd >/dev/null 2>&1; then
    running=1
fi

[ "$running" -eq 1 ] || exit 0

count=$(docker ps -q 2>/dev/null | wc -l)

# Plain text, no embedded #[fg=...] escapes -- those existed for the old
# solid-fill pill design (dark text needed on a light background). The
# "hollow pill" design (tmux.conf) gives every module exactly one uniform
# color for its border and text together, applied by the wrapping module
# in tmux.conf, not per-script -- icon and the real running-container
# count logic above are unchanged.
printf '%s  x %s' "$icon" "$count"
