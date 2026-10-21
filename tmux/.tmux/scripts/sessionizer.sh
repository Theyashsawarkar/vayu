#!/usr/bin/env bash
# Session picker popup (prefix s): sessions only, live preview of each one.
#   sessionizer.sh <client>
# keybind: Tmux/session picker | Enter | Switch to the highlighted session
# keybind: Tmux/session picker | Ctrl+x | Kill the highlighted session (not the current one)
# keybind: Tmux/session picker | Ctrl+n | Create a session named after the typed text, even if it matches one
# keybind: Tmux/session picker | new name + Enter | Create a session with that name in ~ and switch to it (when nothing matches)
# keybind: Tmux/session picker | Esc | Close the session picker
#
# Every tmux call is pinned to <client>: with more than one kitty window
# attached, a bare switch-client would move whichever client tmux guesses.
# Theme colours from varna, when it is installed (fallback: the colours below).
[ -r "${XDG_STATE_HOME:-$HOME/.local/state}/varna/fzf.sh" ] && . "${XDG_STATE_HOME:-$HOME/.local/state}/varna/fzf.sh"

rose=$'\e[38;2;208;149;164m' gold=$'\e[38;2;212;178;92m' dim=$'\e[38;2;108;112;134m'
fg=$'\e[38;2;215;221;230m' sub=$'\e[38;2;154;159;170m' b=$'\e[1m' r=$'\e[0m'
key=$'\e[1;38;2;208;149;164m'

client=$1
[ "$client" = --list ] && client=$2

# One entry per session, NUL-separated so it can span two lines:
#   name <TAB> line 1 (dot, name, tag) <TAB> line 2 (windows, directory)
# Only line 1 is searched (--nth 1), so typing a new name isn't swallowed
# by a match on some window name.
list() {
  local cur; cur=$(tmux display -p -c "$client" '#{client_session}')
  tmux list-sessions -F '#{session_name}	#{session_windows}	#{session_attached}	#{session_path}' |
  while IFS=$'\t' read -r name wins att path; do
    local dot="${dim}○" col=$fg tag=""
    [ "$att" -gt 0 ] && tag="  ${dim}attached elsewhere"
    [ "$name" = "$cur" ] && { dot="${gold}●"; col=$gold; tag="  ${gold}current"; }
    local names; names=$(tmux list-windows -t "=$name" -F '#W' | paste -sd, | sed 's/,/ · /g')
    printf '%s\t %s %s%s%s%s\t\n   %s󰖯 %s window%s%s  %s%s\n   %s %s%s\0' \
      "$name" "$dot" "$col$b" "$name" "$r" "$tag$r" \
      "$sub" "$wins" "$([ "$wins" = 1 ] || echo s)" "$dim" "$names" "$r" \
      "$dim" "${path/#$HOME/\~}" "$r"
  done
}

[ "$1" = --list ] && { list; exit; }

footer="${key}enter${r}   ${fg}switch session${r}     ${key}ctrl-x${r}  ${fg}kill session${r}
${key}ctrl-n${r}  ${fg}new from name${r}      ${key}esc${r}     ${fg}close${r}"

out=$(list | SHELL=bash fzf --ansi --read0 --gap --delimiter '\t' --with-nth 2.. --nth 1 \
  --print-query --expect ctrl-n \
  --layout reverse --info inline-right --no-separator --no-scrollbar --highlight-line \
  --prompt '  ' --pointer '▌' --marker ' ' --gutter ' ' \
  --input-border rounded --input-label ' search, or type a new session name ' --input-label-pos 3 \
  --list-border rounded \
  --footer "$footer" --footer-border rounded --footer-label ' keys ' --footer-label-pos 3 \
  --preview "tmux capture-pane -ep -t ={1}: | awk '/[^[:space:]]/{for(;n;n--)print \"\";print;next}{n++}'" \
  --preview-window 'right,55%,border-rounded,follow' \
  --preview-label ' preview ' \
  --bind "ctrl-x:execute-silent(if [ {1} = \"\$(tmux display -p -c '$client' '#{client_session}')\" ]; then notify-send -a tmux -i utilities-terminal tmux 'Switch away before killing the current session'; else tmux kill-session -t ={1}; fi)+reload($0 --list '$client')" \
  --color "${VARNA_FZF_COLORS:-bg:-1,bg+:#2A2D35,fg:#D7DDE6,fg+:#FFFFFF,hl:#D095A4,hl+:#D095A4,border:#D095A4,label:#D095A4,prompt:#D095A4,pointer:#D095A4,info:#6C7086,query:#D7DDE6,input-border:#D095A4,list-border:#3B4048,list-label:#D095A4,footer-border:#3B4048,footer-label:#6C7086,preview-border:#3B4048,preview-label:#6C7086}")

query=$(sed -n 1p <<<"$out")
pressed=$(sed -n 2p <<<"$out")
pick=$(sed -n 3p <<<"$out" | cut -f1)

if [ "$pressed" != ctrl-n ] && [ -n "$pick" ]; then
  tmux switch-client -c "$client" -t "=$pick"
elif [ -n "$query" ]; then
  name=$(tr '.: ' '___' <<<"$query")
  tmux has-session -t "=$name" 2>/dev/null || tmux new-session -ds "$name" -c "$HOME"
  tmux switch-client -c "$client" -t "=$name"
fi
