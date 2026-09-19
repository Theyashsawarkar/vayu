#!/usr/bin/env bash
# Floating tmux command prompt (popup), laid out like a Neovim cmdline:
# a single rounded, titled input box. Enter runs what you typed, Esc cancels.

sel=$(: | fzf --print-query --no-info --no-separator --no-scrollbar \
      --ghost 'tmux command' --prompt '❯ ' \
      --border none --padding 0 --margin 0 \
      --input-border rounded --input-label ' Cmdline ' --input-label-pos 3 \
      --color 'bg:-1,prompt:#D095A4,query:#D7DDE6,ghost:#6f665c,input-border:#D095A4,input-label:#D095A4' \
      --bind 'enter:accept-or-print-query' | head -n1)

[ -n "$sel" ] && tmux $sel 2>&1 | head -n1 | { read -r err; [ -n "$err" ] && notify-send -a tmux -i utilities-terminal 'tmux' "$err"; }
