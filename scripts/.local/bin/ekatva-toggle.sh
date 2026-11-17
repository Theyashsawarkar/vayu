#!/usr/bin/env bash
# ekatva-toggle.sh [on|off|toggle]: turns ekatva (the phone link) on or off,
# and remembers it: sway-session.sh starts ekatva at login only when it was
# left on. Off by default (no state file), like jyoti's switch.
#
# Off stops ekatva.service: no daemon, no listening port, no phone link, no
# CPU. The quick settings tile (kendra), the bar's capsule (right click) and
# Super+o (when it's off) all come here.
#
# Logs to the journal: journalctl --user -t ekatva-toggle
log() { logger -t ekatva-toggle -- "$*"; }

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/ekatva-switch"
STATE_FILE="$STATE_DIR/enabled"
ICON=/usr/share/icons/candy-icons/apps/scalable/smartphoneconnected.svg
[[ -r $ICON ]] || ICON=phone

want=${1:-toggle}
if [[ $want == toggle ]]; then
    systemctl --user is-active --quiet ekatva.service && want=off || want=on
fi

case $want in
    on)
        mkdir -p "$STATE_DIR" && touch "$STATE_FILE"
        if systemctl --user start ekatva.service; then
            notify-send -a ekatva -u low -i "$ICON" "ekatva on" "Your phone and laptop are linked. Stays on after a reboot."
        else
            log "couldn't start ekatva.service"
            notify-send -a ekatva -u critical -i "$ICON" "ekatva didn't start" "journalctl --user -u ekatva"
        fi
        ;;
    off)
        rm -f "$STATE_FILE"
        systemctl --user stop ekatva.service || log "couldn't stop ekatva.service"
        notify-send -a ekatva -u low -i "$ICON" "ekatva off" "Phone link stopped. Stays off after a reboot."
        ;;
    *)
        echo "usage: ekatva-toggle.sh [on|off|toggle]" >&2
        exit 2
        ;;
esac
# The capsule now (bar-events also follows the unit, a moment later).
"$HOME/.local/bin/waybar-signal" 13 2>/dev/null || true
