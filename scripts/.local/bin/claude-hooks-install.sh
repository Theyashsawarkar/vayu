#!/usr/bin/env bash
# Registers this repo's Claude Code hooks in ~/.claude/settings.json.
# Run by install.sh; safe to re-run any time.
#
# settings.json itself is NOT stowed: Claude Code rewrites it on its own
# (theme, permissions, ...), which would either dirty the repo or replace
# the symlink with a plain file. So the hook is *merged* in with jq:
# created if the file is missing, added if absent, left alone if present,
# and every other setting is preserved.
#
# Hooks:
#   PostToolUse Edit|Write|MultiEdit -> keybind-check-hook.sh
#     after any edit to a keybinding source, runs keybind-search.py --check
#     and reports failures back to Claude (see ~/dotfiles/CLAUDE.md).
set -euo pipefail

settings="$HOME/.claude/settings.json"
cmd="~/.local/bin/keybind-check-hook.sh"

mkdir -p "${settings%/*}"
[ -s "$settings" ] || echo '{}' > "$settings"

if jq -e --arg c "$cmd" '[.hooks.PostToolUse[]?.hooks[]?.command] | index($c)' "$settings" >/dev/null; then
  echo "keybinding hook already registered in $settings"
  exit 0
fi

tmp=$(mktemp)
jq --arg c "$cmd" '
  .hooks.PostToolUse = ((.hooks.PostToolUse // []) + [{
    matcher: "Edit|Write|MultiEdit",
    hooks: [{type: "command", command: $c, timeout: 30,
             statusMessage: "Checking keybinding registry..."}]
  }])' "$settings" > "$tmp"
mv "$tmp" "$settings"
echo "registered keybinding hook in $settings"
