#!/usr/bin/env bash
# Super+o: opens ekatva's window, Darpaṇa (a Vyom popup; instant: Vyom is already running).
# Super+Ctrl+o passes "pair". When ekatva is off it says so instead of
# failing silently, and opening never turns it on by itself (that is the
# switch's job: quick settings, or ekatva-toggle.sh on).
if ! systemctl --user is-active --quiet ekatva.service; then
    notify-send -a ekatva -u low -i phone "ekatva is off" "Turn it on in quick settings (Super+q), then Super+o opens it."
    exit 0
fi
# By its full path: sway's PATH has no ~/.local/bin (its own keys use the same path).
vyom=$HOME/.local/bin/vyom
command -v "$vyom" >/dev/null 2>&1 || vyom=$(command -v vyom)
if [ -n "$vyom" ]; then
    exec "$vyom" darpana "$@"
fi
exec "$HOME/.local/bin/ekatva" window "$@"
