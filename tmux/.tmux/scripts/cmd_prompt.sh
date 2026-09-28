#!/usr/bin/env bash
# Floating tmux prompt (popup), laid out like a Neovim cmdline: a single
# rounded, titled input box. Enter runs what you typed, Esc cancels.
#   cmd_prompt.sh <client> <outfile> [label] [initial-format] [command]
#
#   no [command]   the line is a tmux command            (prefix :)
#   [command]      the line is its quoted argument, e.g. "rename-window --"
#                  with [initial-format] "#{window_name}" prefilled
#
# The popup only *collects* the line -- it never runs `tmux ...` itself.
# A tmux client started from inside a popup attaches to the popup's own
# pty, so `new -s foo` used to open a whole nested tmux inside the popup.
# Instead the line goes to <outfile>, and the binding sources that file
# once this script returns, i.e. in the real client's context, exactly
# like tmux's built-in prompts.

if [ "$1" = --input ]; then
  : | fzf --print-query --no-info --no-separator --no-scrollbar \
      --ghost "$3" --prompt '❯ ' --query "$4" \
      --border none --padding 0 --margin 0 \
      --input-border rounded --input-label " $3 " --input-label-pos 3 \
      --color 'bg:-1,prompt:#D095A4,query:#D7DDE6,ghost:#6f665c,input-border:#D095A4,input-label:#D095A4' \
      --bind 'enter:accept-or-print-query' | head -n1 > "$2"
  exit 0
fi

c=$1 out=$2 label=${3:-Cmdline} init=$4 cmd=$5
mkdir -p "${out%/*}"
rm -f "$out"   # a cancelled prompt must never re-run the previous command
[ -n "$init" ] && init=$(tmux display -p -c "$c" "$init")

q() { printf '%q' "$1"; }
tmux display-popup -c "$c" -E -B -w 50% -h 3 -x C -y C -s "bg=default" \
  "$(q "$0") --input $(q "$out") $(q "$label") $(q "$init")" || true

# Argument mode: wrap the typed text as one tmux-quoted argument
# (double quotes, with \ " $ escaped and # doubled so nothing expands).
if [ -n "$cmd" ] && [ -s "$out" ]; then
  arg=$(sed -e 's/[\\"$]/\\&/g' -e 's/#/##/g' "$out")
  printf '%s "%s"\n' "$cmd" "$arg" > "$out"
fi

# Parse-check first: a typo'd command goes to mako (like every other tmux
# notification) instead of tmux dumping "file:1: unknown command" in a
# view-mode pane. Runtime errors (e.g. a missing target) still show in
# the status line, same as the built-in prompt.
if [ -s "$out" ] && ! err=$(tmux source-file -n "$out" 2>&1); then
  rm -f "$out"
  notify-send -a tmux -i utilities-terminal 'tmux' "${err#*: }"
fi
