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
dbus-update-activation-environment --all
systemctl --user start sway-session.target

# Returns on the shutdown event, or with an error if sway dies without
# sending one. Either way the session is over.
swaymsg -t subscribe '["shutdown"]' >/dev/null 2>&1
systemctl --user stop sway-session.target
systemctl --user unset-environment WAYLAND_DISPLAY SWAYSOCK I3SOCK DISPLAY
