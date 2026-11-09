#!/usr/bin/env bash
# Session picker popup (prefix s): sessions only, live preview of each one.
#   sessionizer.sh <client>
# Starts in INSERT (type to search); Esc goes to NORMAL (fzf-vim.sh: j/k,
# gg/G, i/a or slash type again, q or Esc closes).
# keybind: Tmux/session picker | Enter | Switch to the highlighted session
# keybind: Tmux/session picker | Ctrl+j / Ctrl+k | Move to the next / previous session (no arrows needed)
# keybind: Tmux/session picker:normal | dd | Kill the highlighted session (asks first: y kills, any other key keeps it)
# keybind: Tmux/session picker | Ctrl+x | Kill the highlighted session (asks first: y kills, any other key keeps it)
# keybind: Tmux/session picker | Ctrl+n | Create a session named after the typed text, even if it matches one
# keybind: Tmux/session picker | new name + Enter | Create a session with that name in ~ and switch to it (when nothing matches)
# keybind: Tmux/session picker:insert | Esc | Enter normal mode (Esc again closes the picker)
#
# Every tmux call is pinned to <client>: with more than one kitty window
# attached, a bare switch-client would move whichever client tmux guesses.
# Theme colours from varna, when it is installed (fallback: the colours below).
# Errors to the journal when nothing would show them (tmux `run -b` drops
# stderr): read them with `vayu-logs sessionizer.sh`.
[ -t 2 ] || [ "${JOURNAL_STREAM:-}" = "$(stat -Lc %d:%i /proc/self/fd/2 2>/dev/null)" ] || exec 2> >(logger -t sessionizer.sh)
[ -r "${XDG_STATE_HOME:-$HOME/.local/state}/varna/fzf.sh" ] && . "${XDG_STATE_HOME:-$HOME/.local/state}/varna/fzf.sh"

# The current session takes the accent (like its capsule on the bar), keys
# the second accent; without varna, Vayu's own colours.
c() { printf '\e[%s38;2;%sm' "$2" "$1"; }
accent=$(c "${VARNA_RGB_ACCENT:-203;166;247}") dim=$(c "${VARNA_RGB_MUTED:-108;112;134}")
fg=$(c "${VARNA_RGB_FG:-215;221;230}") sub=$(c "${VARNA_RGB_SUBTEXT0:-154;159;170}") b=$'\e[1m' r=$'\e[0m'
key=$(c "${VARNA_RGB_ACCENT2:-245;194;231}" '1;')

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
    [ "$name" = "$cur" ] && { dot="${accent}●"; col=$accent; tag="  ${accent}current"; }
    local names; names=$(tmux list-windows -t "=$name" -F '#W' | paste -sd, | sed 's/,/ · /g')
    printf '%s\t %s %s%s%s%s\t\n   %s󰖯 %s window%s%s  %s%s\n   %s %s%s\0' \
      "$name" "$dot" "$col$b" "$name" "$r" "$tag$r" \
      "$sub" "$wins" "$([ "$wins" = 1 ] || echo s)" "$dim" "$names" "$r" \
      "$dim" "${path/#$HOME/\~}" "$r"
  done
}

[ "$1" = --list ] && { list; exit; }

# --kill <session> <client>: after the y of "kill this session?"; never the
# session this client is on.
if [ "$1" = --kill ]; then
  if [ "$2" = "$(tmux display -p -c "$3" '#{client_session}')" ]; then
    notify-send -a tmux -i utilities-terminal tmux 'Switch away before killing the current session'
  else
    tmux kill-session -t "=$2"
  fi
  exit 0
fi

. ~/.tmux/scripts/fzf-vim.sh
ask="change-input-label( kill this session? y kills it, any other key keeps it )"
declare -A FZF_VIM_SEQ=([d]="$ask")
fzf_vim ' search, or type a new session name '
# y: only means something right after the question
kill_bind="y:transform:case \$FZF_INPUT_LABEL in *'kill this session'*) echo \"execute-silent($0 --kill {1} $client)+reload($0 --list $client)+$FZF_VIM_BACK\" ;; *) echo '$FZF_VIM_BACK' ;; esac"

footer="${key}enter${r}   ${fg}switch session${r}     ${key}ctrl-x${r} ${dim}or${r} ${key}dd${r}  ${fg}kill session${r}     ${key}ctrl-j/k${r}  ${fg}move${r}
${key}ctrl-n${r}  ${fg}new from name${r}      ${key}esc${r}  ${fg}normal mode, again closes${r}    ${key}i${r}  ${fg}type${r}"

out=$(list | SHELL=bash fzf --ansi --read0 --gap --delimiter '\t' --with-nth 2.. --nth 1 \
  --print-query --expect ctrl-n \
  --layout reverse --info inline-right --no-separator --no-scrollbar --highlight-line \
  --prompt '  ' --pointer '▌' --marker ' ' --gutter ' ' \
  --input-border rounded --input-label-pos 3 "${FZF_VIM_OPTS[@]}" --bind "$kill_bind" \
  --list-border rounded \
  --footer "$footer" --footer-border rounded --footer-label ' keys ' --footer-label-pos 3 \
  --preview "tmux capture-pane -ep -t ={1}: | awk '/[^[:space:]]/{for(;n;n--)print \"\";print;next}{n++}'" \
  --preview-window 'right,55%,border-rounded,follow' \
  --preview-label ' preview ' \
  --bind "ctrl-x:$FZF_VIM_NORMAL+$ask" \
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
