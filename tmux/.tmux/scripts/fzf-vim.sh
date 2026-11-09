#!/usr/bin/env bash
# Normal and Insert modes for an fzf picker (the Space grammar,
# docs/KEYBINDINGS.md). A picker starts in INSERT (typing searches, as
# before); Esc goes to NORMAL, where letters are commands and typing
# changes nothing; Esc again closes. i, a or / go back to INSERT.
#
#   . ~/.tmux/scripts/fzf-vim.sh
#   declare -A FZF_VIM_KEYS=([n]='print(new)+accept')   # extra NORMAL keys
#   declare -A FZF_VIM_SEQ=([d]='execute(...)+reload(...)')  # dd, yy...: a doubled key
#   fzf_vim ' sessions '                 # fills the FZF_VIM_OPTS array
#   fzf "${FZF_VIM_OPTS[@]}" ...
#
#   fzf-vim.sh --print0 ' label '      # the same options, NUL-separated (for Python)
#
# The mode is shown in the input label (" INSERT · sessions "); a pending
# first key of a pair shows too (" NORMAL d · sessions "). fzf has no key
# sequences, so gg and dd are done by remembering the first key in the
# label. Run fzf with SHELL=bash: the transforms are bash.
#
# keybind: Tmux/every picker:insert | Esc | Enter normal mode (letters stop typing)
# keybind: Tmux/every picker:normal | j / k | Move down / up
# keybind: Tmux/every picker:normal | gg / G | Jump to the first / last entry
# keybind: Tmux/every picker:normal | Ctrl+d / Ctrl+u | Scroll half a page down / up
# keybind: Tmux/every picker:normal | i / a / slash | Enter insert mode (type to search)
# keybind: Tmux/every picker:normal | q / Esc | Close the picker (Esc first cancels a pending key)

fzf_vim() {
  local base=$1 k all=() rest=() act
  # Every key that types: bound in NORMAL (a command or nothing), unbound
  # in INSERT so it reaches the query.
  # (every printable but , ( ) and ': the list is comma-separated and the
  # actions are quoted with ' -- those four still type in NORMAL)
  for k in {a..z} {A..Z} {0..9} / ? - . _ space : \; = + '*' '~' ! @ '#' % ^ '&' \
           '[' ']' '{' '}' '<' '>' '|' '"' '$' '\' '`'; do all+=("$k"); done
  local list; list=$(IFS=,; echo "${all[*]}")
  local ins="unbind($list)+change-input-label( INSERT ·$base)"
  local nor="rebind($list)+change-input-label( NORMAL ·$base)"
  local back="change-input-label( NORMAL ·$base)"
  # for the caller's own binds: back to plain NORMAL, and the key list
  FZF_VIM_BACK=$back FZF_VIM_LIST=$list FZF_VIM_NORMAL=$nor

  FZF_VIM_OPTS=(--input-label " INSERT ·$base" --bind "start:unbind($list)")
  # Esc: cancel a pending key, else close from NORMAL, else go to NORMAL.
  FZF_VIM_OPTS+=(--bind "esc:transform:case \$FZF_INPUT_LABEL in *' NORMAL ? ·'*) echo '$back' ;; *' NORMAL ·'*) echo abort ;; *) echo '$nor' ;; esac")

  # Ctrl+d / Ctrl+u: half pages in NORMAL, fzf's own line editing in INSERT
  FZF_VIM_OPTS+=(--bind "ctrl-d:transform:case \$FZF_INPUT_LABEL in *' NORMAL'*) echo 'half-page-down+$back' ;; *) echo delete-char/eof ;; esac")
  FZF_VIM_OPTS+=(--bind "ctrl-u:transform:case \$FZF_INPUT_LABEL in *' NORMAL'*) echo 'half-page-up+$back' ;; *) echo unix-line-discard ;; esac")
  declare -A map=(
    [j]="down+$back" [k]="up+$back" [G]="last+$back" [q]="abort"
    [i]="$ins" [a]="$ins" [/]="$ins"
  )
  # extra single keys from the caller
  if declare -p FZF_VIM_KEYS >/dev/null 2>&1; then
    for k in "${!FZF_VIM_KEYS[@]}"; do map[$k]="${FZF_VIM_KEYS[$k]}+$back"; done
  fi
  # pairs: g (gg = first) and the caller's (dd, yy...)
  declare -A seq=([g]="first")
  if declare -p FZF_VIM_SEQ >/dev/null 2>&1; then
    for k in "${!FZF_VIM_SEQ[@]}"; do seq[$k]="${FZF_VIM_SEQ[$k]}"; done
  fi
  for k in "${!seq[@]}"; do
    local pend="change-input-label( NORMAL $k ·$base)"
    # Actions are passed through printf %q-free single quotes: they must
    # not contain a single quote themselves.
    # an action that sets its own label (a confirm question) keeps it
    act=${seq[$k]}; [[ $act == *change-input-label* ]] || act="$act+$back"
    map[$k]="transform:case \$FZF_INPUT_LABEL in *' NORMAL $k ·'*) echo '$act' ;; *) echo '$pend' ;; esac"
  done
  for k in "${all[@]}"; do
    act=${map[$k]:-$back}   # any other key: nothing (and cancels a pending key)
    # While a question shows (a label with "? y": "kill this session? y
    # kills it…"), a plain key only answers no: it doesn't also move.
    [[ $act == transform:* || $act == abort ]] || act=$(fzf_vim_guard "$act")
    FZF_VIM_OPTS+=(--bind "$k:$act")
  done
  # Enter and the moving keys also answer no to a question, instead of
  # switching to (or moving off) the entry it asks about.
  for k in enter ctrl-j ctrl-k down up; do
    case $k in enter) act=accept ;; ctrl-j|down) act=down ;; *) act=up ;; esac
    FZF_VIM_OPTS+=(--bind "$k:$(fzf_vim_guard "$act")")
  done
}

# fzf_vim_guard <action>: the action, or just "back to NORMAL" while a
# question ("… ? y …") is in the label. The action must not contain '.
fzf_vim_guard() {
  printf "%s" "transform:case \$FZF_INPUT_LABEL in *'? y '*) echo '$FZF_VIM_BACK' ;; *) echo '$1' ;; esac"
}

if [ "${1:-}" = --print0 ]; then
  fzf_vim "${2:- }"
  printf '%s\0' "${FZF_VIM_OPTS[@]}"
fi
