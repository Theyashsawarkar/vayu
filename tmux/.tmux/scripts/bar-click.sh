#!/usr/bin/env bash
# A click on one of the bar's capsules (status ranges), from tmux.conf's
# MouseDown1Status: bar-click.sh <client> <range> <pane path>
#   prs        sangam in a popup (like prefix G)
#   claude     jump to the Claude session that has waited longest (like prefix a)
#   usage      vesha in a popup, the Claude accounts and their usage (like prefix C)
#   dev*       pattan in a popup, the dev servers and their ports (like prefix P)
#   docker     nauka in a popup, Docker (like prefix D)
#   mail/chat  sandesh in a popup, on its mail or chat tab (like prefix e)
# Errors to the journal when nothing would show them (tmux `run -b` drops
# stderr): read them with `vayu-logs bar-click.sh`.
[ -t 2 ] || [ "${JOURNAL_STREAM:-}" = "$(stat -Lc %d:%i /proc/self/fd/2 2>/dev/null)" ] || exec 2> >(logger -t bar-click.sh)
client=$1 range=$2 path=$3
case "$range" in
  prs) exec ~/.tmux/scripts/popup.sh "$client" -E -d "$path" -T ' 󰊤 sangam ' ~/.tmux/plugins/sangam/bin/sangam --popup G ;;
  claude) exec ~/.local/bin/claude-tmux next ;;
  usage) exec ~/.tmux/scripts/popup.sh "$client" -E -d "$path" -T ' 󰚩 vesha ' "$HOME/.local/bin/vesha" ;;
  dev*) exec ~/.tmux/scripts/popup.sh "$client" -E -d "$path" -T ' 󰒋 pattan ' ~/.tmux/plugins/pattan/scripts/pattan-run --popup P --client "$client" ;;
  mail | chat) exec ~/.tmux/scripts/popup.sh "$client" -E -d "$path" -T ' 󰇮 sandesh ' ~/.tmux/plugins/sandesh/scripts/sandesh-run --popup --tab "$range" ;;
  docker) exec ~/.tmux/scripts/popup.sh "$client" -E -d "$path" -T " $(printf '\uf308') nauka " ~/.tmux/plugins/nauka/scripts/nauka-run --popup D ;;
esac
