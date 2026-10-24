#!/bin/sh
# Ties the systemd --user session to sway's lifetime. Run once from
# sway/config. Waits for sway to shut down, then undoes the setup.
#
# 1. Import WAYLAND_DISPLAY/SWAYSOCK etc. into the user manager (and D-Bus
#    activation) environment, so user services can reach the compositor.
# 2. Start sway-session.target, which binds graphical-session.target.
# 3. On sway's shutdown event, stop it: every PartOf=graphical-session.target
#    unit (idle units, bar-events, kdeconnect, portals...) stops with it.
#    Otherwise they outlive sway, since the user manager lingers across
#    logout, and crash-loop with no compositor. Then unset the display
#    variables so later D-Bus activations don't try to reach the dead
#    compositor either.
#
# Logs to the journal: journalctl --user -t sway-session
log() { logger -t sway-session -- "$*"; }

# A unit that failed in the last session (a crash, a start limit hit) would
# stay failed, and some won't start again until reset.
systemctl --user reset-failed
dbus-update-activation-environment --all
systemctl --user start sway-session.target || log "couldn't start sway-session.target"
# The session's services, all here and only after the import above: when
# sway's config started them itself (`exec systemctl --user restart ...`)
# they raced this import, and one that won started without WAYLAND_DISPLAY
# for good. Each is a unit, so a crash restarts it (with backoff) and its
# output lands in the journal under its own name (vayu-logs <name>).
UNITS="mako.service waybar.service vyom.service nada.service bar-events.service
  kdeconnect.service phone-events.service sway-audio-idle-inhibit.service
  swaylock-on-sleep.service batsignal.service cliphist@text.service cliphist@image.service
  pramana.service drishya.service"
# shellcheck disable=SC2086 # a list of unit names
for u in $UNITS; do
  systemctl --user restart "$u" || log "couldn't start $u (journalctl --user -u $u)"
done
# Last chosen notification mode (mako resets it on start), and swayidle
# unless caffeine mode was left on: both need mako / the compositor.
"$HOME/.local/bin/notification-mode-restore.sh" &
"$HOME/.local/bin/swayidle-startup.sh" &
log "session started (WAYLAND_DISPLAY=$WAYLAND_DISPLAY)"

# Returns on the shutdown event, or with an error if sway dies without
# sending one. Either way the session is over.
swaymsg -t subscribe '["shutdown"]' >/dev/null 2>&1
log "sway shut down: stopping the graphical session"
# Unset first, so nothing D-Bus-activated from here on reaches for the
# dead compositor. Then stop, and make sure graphical-session.target really
# stops: systemd refuses ("transaction is destructive") while a portal's
# start job is still queued, which left the portals running with no
# compositor, crash-looping until their start limit.
systemctl --user unset-environment WAYLAND_DISPLAY SWAYSOCK I3SOCK DISPLAY
dbus-update-activation-environment WAYLAND_DISPLAY= SWAYSOCK= I3SOCK= DISPLAY= 2>/dev/null
for try in 1 2 3 4 5; do
  systemctl --user stop sway-session.target graphical-session.target 2>/dev/null
  systemctl --user is-active --quiet graphical-session.target || { log "graphical session stopped"; exit 0; }
  sleep 1
done
log "graphical-session.target still active after $try tries"
