#!/usr/bin/env bash
# Claude Code PostToolUse hook (Edit|Write|MultiEdit, ~/.claude/settings.json):
# after an edit to any keybinding source, run keybind-search.py --check and
# hand failures back to Claude (exit 2 + stderr) so an undescribed or
# duplicate binding never slips past the central keybinding search.
# Everything else is a silent no-op. See ~/dotfiles/CLAUDE.md.

f=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty')
[ -n "$f" ] || exit 0
real=$(realpath -m -- "$f")

case $real in
  */sway/config|*/sway/.config/sway/config) ;;
  */tmux/tmux.conf) ;;
  */kitty/kitty.conf) ;;
  */zed/keymap.json) ;;
  */rmpc/config.ron) ;;
  */.tmux/scripts/*|*/scripts/.local/bin/*|*/.local/bin/*|*/sway/scripts/*) ;;
  *) exit 0 ;;
esac

check=~/.local/bin/keybind-search.py
case $real in
  */tmux.conf) out=$("$check" --check --tmux-conf "$real" 2>&1) ;;  # the edited file, not the live server
  *)           out=$("$check" --check 2>&1) ;;
esac
[ $? -eq 0 ] && exit 0

{
  echo "Keybinding registry check failed after editing $f:"
  echo "$out"
  echo "Every keybinding must be described so Super+Shift+/ (and tmux prefix ?) list it -- see ~/dotfiles/CLAUDE.md."
} >&2
exit 2
