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

# Plain text, no embedded #[fg=...] escapes -- the filled-pill design
# (tmux.conf) wraps this whole module in bg=<role color>,fg=#1E1E2E
# itself, so the color (dark ink on a solid Amber fill) is applied once,
# centrally, by the wrapping module in tmux.conf, not per-script. Same
# reasoning held even through the earlier "hollow pill" design in between
# -- icon and the real running-container count logic above are unchanged.
printf '%s  x %s' "$icon" "$count"
