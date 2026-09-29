#!/usr/bin/env bash
# Applies caffeine mode's persisted state at sway startup, run from
# sway/config in place of an unconditional `systemctl --user restart
# swayidle.service`.
#
# Why this exists: swayidle.service is `enabled` (WantedBy=default.target),
# so systemd's user manager auto-starts it at every login on its own,
# completely independent of sway -- caffeine mode (stopping the service)
# never survived a reboot/login because of this, no matter what state it
# was left in before. This script is the single source of truth for what
# swayidle's state should be at this point in startup: if caffeine was on
# (marker file present, written by caffeine-toggle.sh), it stops the
# service systemd just auto-started, overriding that; otherwise it does
# the normal restart -- still needed for the env-var-ordering reason
# documented in sway/config right above this exec line (swayidle started
# by systemd at login can predate dbus-update-activation-environment).
STATE_FILE="$HOME/.local/state/caffeine/enabled"

# reset-failed first -- found live, not assumed: systemd's own
# auto-start (WantedBy=default.target) races dbus-update-activation-
# environment and fails 4 times in ~7 seconds, well before this script
# ever runs, which burns through systemd's default start-limit-burst
# (5 failures / 10s). Once that limit is hit, the unit sits in
# "start-limit-hit" and a plain `restart` from here is a silent no-op --
# confirmed directly: swayidle stayed inactive (dead) after a real
# reboot, on every boot, and `systemctl --user restart` alone did
# nothing until `reset-failed` ran first. This is exactly the same
# WAYLAND_DISPLAY race sway-audio-idle-inhibit.service already had a
# comment about, just needing this extra step since that one only
# fails once (not enough to hit the burst limit) where swayidle fails
# fast enough to exhaust it every time.
systemctl --user reset-failed swayidle.service

if [ -e "$STATE_FILE" ]; then
    systemctl --user stop swayidle.service
else
    systemctl --user restart swayidle.service
fi

# Refresh the waybar capsule now (it only polls once a minute as a fallback).
pkill -RTMIN+12 waybar 2>/dev/null || true
