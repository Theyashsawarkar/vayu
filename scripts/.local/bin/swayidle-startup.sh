#!/usr/bin/env bash
# Starts swayidle.service at sway startup unless caffeine mode was left on
# (marker file written by caffeine-toggle.sh), so caffeine survives a
# reboot. Run from sway/config after dbus-update-activation-environment.
#
# swayidle.service has no [Install] section, so nothing else starts it:
# this is the single source of truth for its state at login. (It used to
# be WantedBy=default.target, which started it before sway existed; it
# crash-looped, hit systemd's start limit, and needed a reset-failed here.)
STATE_FILE="$HOME/.local/state/caffeine/enabled"

[ -e "$STATE_FILE" ] || systemctl --user start swayidle.service

# Refresh the waybar capsule now (bar-events.py also sees swayidle's state
# change, 0.3 s later).
"$HOME/.local/bin/waybar-signal" 12 2>/dev/null || true
