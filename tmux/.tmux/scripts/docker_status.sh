#!/usr/bin/env bash
# Docker segment for the tmux status bar.
#
# Always prints a docker icon + running-container count, 0 while the
# daemon is stopped -- same as waybar's docker-status.sh. The pill itself
# (caps, fill, padding) lives in tmux.conf, so printing nothing here left
# an empty blue capsule on the bar.
#
# docker is socket-activated (install.sh), so `docker ps` against a stopped
# daemon would start it -- every status tick, from this segment. Only ask
# docker once it is actually running.

icon=$'' # nf-linux-docker (U+F308)

count=0
systemctl is-active --quiet docker.service && count=$(docker ps -q 2>/dev/null | wc -l)

# Plain text, no embedded #[fg=...] escapes -- tmux.conf wraps this whole
# module in its filled pill (dark ink on a solid fill) centrally.
printf '%s  x %s' "$icon" "$count"
