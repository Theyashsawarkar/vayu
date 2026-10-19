#!/usr/bin/env bash
# Exit 0 if a `set -g @plugin 'owner/repo'` in tmux.conf isn't cloned in
# ~/.tmux/plugins yet (tmux.conf then runs TPM's installer), 1 if all are.
conf=${XDG_CONFIG_HOME:-$HOME/.config}/tmux/tmux.conf
while read -r spec; do
  [ -d "$HOME/.tmux/plugins/${spec##*/}" ] || exit 0
done < <(sed -nE "s/^set -g @plugin '([^']+)'.*/\1/p" "$conf")
exit 1
