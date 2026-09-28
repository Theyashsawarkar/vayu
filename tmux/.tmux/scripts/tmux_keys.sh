#!/usr/bin/env bash
# prefix ?: fuzzy-search every tmux keybinding -- the same live registry as
# the desktop-wide Super+Shift+/ search (keybind-search.py) -- and run the
# picked one, exactly as if its keys had been typed.
#   tmux_keys.sh <client>
# keybind: Tmux/key search | Enter | Run the highlighted binding
# keybind: Tmux/key search | Esc | Close without running anything
#
# The binding is replayed with `send-keys -K` (keys go through the client's
# key tables) only after the popup has closed; while it's open the popup
# would swallow them. Copy-mode keys enter copy mode first.

c=$1
out=$(mktemp)
trap 'rm -f "$out"' EXIT

~/.tmux/scripts/popup.sh "$c" 80 75 -E -B "$HOME/.local/bin/keybind-search.py --tmux-fzf > '$out'"

IFS=$'\t' read -r table key < "$out"
[ -n "$key" ] && [ "$key" != - ] || exit 0
[ "$key" = ';' ] && key='\;'   # a bare ; argument is tmux's command separator

case $table in
  prefix) tmux send-keys -K -c "$c" "$(tmux show -gv prefix)" "$key" ;;
  root)   tmux send-keys -K -c "$c" "$key" ;;
  copy-mode*)
    tmux copy-mode -t "$(tmux display -p -c "$c" '#{pane_id}')"
    tmux send-keys -K -c "$c" "$key" ;;
esac
exit 0
