#!/usr/bin/env bash
# Session picker popup (prefix s): sessions only, live preview of each one.
#   sessionizer.sh <client>
#   enter   switch        ctrl-x  kill (not the current one)
#   type a name that doesn't exist + enter -> create it in ~
#
# Every tmux call is pinned to <client>: with more than one kitty window
# attached, a bare switch-client would move whichever client tmux guesses.

rose=$'\e[38;2;208;149;164m' gold=$'\e[38;2;212;178;92m' dim=$'\e[38;2;108;112;134m'
fg=$'\e[38;2;215;221;230m' r=$'\e[0m'

client=$1
[ "$client" = --list ] && client=$2

list() {
  local cur; cur=$(tmux display -p -c "$client" '#{client_session}')
  tmux list-sessions -F '#{session_name}	#{session_windows}	#{session_attached}' |
  while IFS=$'\t' read -r name wins att; do
    local dot="${dim}○" col=$fg tag=""
    [ "$att" -gt 0 ] && tag="${dim}  attached"
    [ "$name" = "$cur" ] && { dot="${gold}●"; col=$gold; tag="${gold}  current"; }
    printf '%s\t %s %s%-22s%s %s win%s%s\n' "$name" "$dot" "$col" "$name" "$dim" "$wins" "$([ "$wins" = 1 ] || echo s)" "$tag$r"
  done
}

[ "$1" = --list ] && { list; exit; }

out=$(list | SHELL=bash fzf --ansi --delimiter '\t' --with-nth 2 --print-query \
  --layout reverse --info inline-right --no-separator --no-scrollbar \
  --prompt '❯ ' --pointer '▌' --marker ' ' --gutter ' ' \
  --border rounded --border-label ' 󰍹 sessions ' --border-label-pos 3 \
  --padding 1,2 \
  --header $'⏎ switch · ^x kill · new name ⏎ creates\n' \
  --preview "tmux capture-pane -ep -t ={1}: | awk '/[^[:space:]]/{for(;n;n--)print \"\";print;next}{n++}'" \
  --preview-window 'right,55%,border-left,follow' \
  --preview-label ' preview ' \
  --bind "ctrl-x:execute-silent([ {1} != \"\$(tmux display -p -c '$client' '#{client_session}')\" ] && tmux kill-session -t ={1})+reload($0 --list '$client')" \
  --color "bg:-1,bg+:#2A2D35,fg:#D7DDE6,fg+:#FFFFFF,hl:#D095A4,hl+:#D095A4" \
  --color "border:#D095A4,label:#D095A4,prompt:#D095A4,pointer:#D095A4,header:#6C7086,info:#6C7086,preview-border:#3B4048,preview-label:#6C7086,query:#D7DDE6")

query=$(sed -n 1p <<<"$out")
pick=$(sed -n 2p <<<"$out" | cut -f1)

if [ -n "$pick" ]; then
  tmux switch-client -c "$client" -t "=$pick"
elif [ -n "$query" ]; then
  name=$(tr '.: ' '___' <<<"$query")
  tmux has-session -t "=$name" 2>/dev/null || tmux new-session -ds "$name" -c "$HOME"
  tmux switch-client -c "$client" -t "=$name"
fi
