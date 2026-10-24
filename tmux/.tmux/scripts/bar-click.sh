#!/usr/bin/env bash
# A click on one of the bar's capsules (status ranges), from tmux.conf's
# MouseDown1Status: bar-click.sh <client> <range> <pane path>
#   prs        sangam in a popup (like prefix G)
#   claude     jump to the Claude session that has waited longest (like prefix a)
#   dev<port>  open http://localhost:<port> in the browser
# Errors to the journal when nothing would show them (tmux `run -b` drops
# stderr): read them with `vayu-logs bar-click.sh`.
[ -t 2 ] || [ "${JOURNAL_STREAM:-}" = "$(stat -Lc %d:%i /proc/self/fd/2 2>/dev/null)" ] || exec 2> >(logger -t bar-click.sh)
client=$1 range=$2 path=$3
case "$range" in
  prs) exec ~/.tmux/scripts/popup.sh "$client" -E -d "$path" -T ' 󰊤 sangam ' ~/.tmux/plugins/sangam/bin/sangam --popup G ;;
  claude) exec ~/.local/bin/claude-tmux next ;;
  dev[0-9]*) exec xdg-open "http://localhost:${range#dev}" >/dev/null 2>&1 ;;
esac
