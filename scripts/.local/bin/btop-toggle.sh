#!/usr/bin/env bash
# Opens btop in its floating window (the bar's CPU/RAM capsule), or closes it
# when it's already open: a click toggles, never a second window on top.
#
# Closing quits it rather than hiding it: btop wakes every 2 s to read every
# process, so a hidden one would keep polling all day for a window that takes
# ~150 ms to open again (dotfiles: fast first, zero waste).
#
# Matched by the kitty's --class, not by sway's window list, so a second
# click before the window has appeared still closes it instead of opening two.
exec 2> >(logger -t btop-toggle)

CLASS=dev.vayu.Btop   # sway's for_window rule floats and sizes it
# [d]: the pattern never matches its own command line (a shell running this).
if pkill -f -- "--class [d]ev\.vayu\.Btop( |$)"; then
    exit 0
fi
exec kitty --class "$CLASS" -e btop -c "${XDG_STATE_HOME:-$HOME/.local/state}/varna/btop.conf"
