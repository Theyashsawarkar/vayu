#!/usr/bin/env bash
# Installs the desktop's AI tools (ai/), root-owned, so an agent running as
# your user can't edit what the approval window shows or what runs as root.
# Run as your user; it calls sudo.
#
#   ai/apply.sh          install whatever differs
#   ai/apply.sh --check  list what differs, exit 1 if anything does
#
# Installs:
#   /usr/local/bin/vayu-elevate                  the CLI / MCP server agents call
#   /usr/local/lib/vayu-elevate/dialog.py        the approval window (GTK4)
#   /usr/local/lib/vayu-elevate/runner.py        runs the approved commands as root
#   /usr/local/lib/vayu-elevate/{config,data}/   empty XDG dirs for the window, so
#                                                user GTK CSS can't restyle it
# Rollback: sudo rm -rf /usr/local/bin/vayu-elevate /usr/local/lib/vayu-elevate
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
check=false
[ "${1:-}" = "--check" ] && check=true

n=0
differs() { n=$((n + 1)); if $check; then echo "differs: $1"; fi; }

deps=(python-gobject gtk4 libadwaita libnotify)
missing=()
for p in "${deps[@]}"; do pacman -Q "$p" >/dev/null 2>&1 || missing+=("$p"); done
if [ "${#missing[@]}" -gt 0 ]; then
  differs "packages not installed: ${missing[*]}"
  $check || sudo pacman -S --needed --noconfirm "${missing[@]}"
fi

lib=/usr/local/lib/vayu-elevate
files=(
  "elevate/vayu-elevate:/usr/local/bin/vayu-elevate"
  "elevate/dialog.py:$lib/dialog.py"
  "elevate/runner.py:$lib/runner.py"
)
for pair in "${files[@]}"; do
  src=$here/${pair%%:*} dst=${pair#*:}
  if cmp -s "$src" "$dst" 2>/dev/null && [ "$(stat -c '%U %a' "$dst")" = "root 755" ]; then continue; fi
  differs "$dst"
  $check || sudo install -Dm755 -o root -g root "$src" "$dst"
done
for d in "$lib" "$lib/config" "$lib/data"; do
  if [ -d "$d" ] && [ "$(stat -c '%U %a' "$d")" = "root 755" ]; then continue; fi
  differs "$d (root-owned directory)"
  $check || sudo install -d -m755 -o root -g root "$d"
done

if $check; then
  [ "$n" -eq 0 ] && echo "AI tools match the repo"
  [ "$n" -eq 0 ]
  exit
fi
[ "$n" -eq 0 ] && { echo "AI tools already up to date"; exit 0; }
echo "AI tools installed: $n change(s). Try: vayu-elevate --why 'Test' --cmd 'id'"
