#!/usr/bin/env bash
# Super+Ctrl+a: pick one of the newest notification's actions in a Vyom
# panel (Accept, Reject, Undo, Show a file in its folder...). A click on
# the popup runs its default action and its buttons show the first three;
# this lists all of them, from the keyboard. `akashvani menu` gives the
# action labels to `vyom dmenu` (stdin: the actions, stdout: the pick, in
# Vyom's order: no cache reshuffling Accept/Reject) and runs the pick.
# keybind: Sway/notification actions | Enter | Run the highlighted notification action
if ! akashvani menu "$HOME/.local/bin/vyom" dmenu -p "Action" 2>/dev/null; then
  notify-send -a akashvani -u low "No actions" "The newest notification has no actions to pick from"
fi
exit 0
