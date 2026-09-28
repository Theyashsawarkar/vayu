#!/usr/bin/env bash
# Super+Ctrl+a: stop the laptop ringing if the phone rang it, otherwise
# pick one of the current notification's actions in wofi (mako's left
# click only ever runs the default one). E.g. Accept/Reject a phone pairing
# request, Undo a clipboard received from the phone, Show a received file
# in its folder.
# keybind: Sway/notification actions | Enter | Run the highlighted notification action
#
# makoctl menu parses every dash-option after it as its own (it rejected
# wofi's -i/-p), so it gets this script back, with no arguments, as the
# picker program; that call runs wofi.
if [ -n "$NOTIFICATION_ACTIONS_PICK" ]; then
  exec wofi --dmenu -i -p "Action "
fi

# A ring comes first and never goes through mako: on 2026-09-29 one could
# not be stopped from its notification, so this kills the player that
# phone-events.py recorded (checked to still be pw-play, not a reused pid).
ring_pid_file="${XDG_RUNTIME_DIR:-/tmp}/find-my-laptop.pid"
if pid=$(cat "$ring_pid_file" 2>/dev/null) && [ "$(cat "/proc/$pid/comm" 2>/dev/null)" = pw-play ]; then
  kill "$pid"
  exit 0
fi
if ! NOTIFICATION_ACTIONS_PICK=1 makoctl menu "$0" 2>/dev/null; then
  notify-send -a mako -u low "No actions" "The current notification has no actions to pick from"
fi
exit 0
