#!/usr/bin/env bash
# Toggles jyoti (ज्योति, the flame) at Akhaṇḍa, the unbroken flame: the laptop stays
# awake -- no dimming, no lock, no sleep from idleness.
#
# With ekatva running, it goes through ekatva (`ekatva jyoti akhanda|off`), the
# one place that holds it: ekatva also holds logind's sleep block and the
# Nandādīpa level the phone can set, so turning it off here really turns it all
# off (this script stopping only swayidle used to leave ekatva's block on,
# and the laptop still wouldn't sleep).
#
# Without ekatva: stops/starts the swayidle user service entirely. That,
# not a logind inhibitor, is what keeps the screen itself on: swayidle's
# 'output * dpms off' talks to sway directly, never through logind.
#
# Modes (the bar's capsule, which only shows while the flame is lit):
#   jyoti-toggle.sh          toggle: Śānta <-> Akhaṇḍa (the key, quick settings)
#   jyoti-toggle.sh off      put it out, whatever the level (left click)
#   jyoti-toggle.sh switch   Akhaṇḍa <-> Nandādīpa (right click)
#   jyoti-toggle.sh akhanda|nandadipa   light it at that level (quick
#                            settings' level buttons)
# Nandādīpa (awake with the lid closed) needs ekatva, which holds logind's
# lid block; without it these say so.
#
# STATE_FILE persists the choice across reboots: swayidle-startup.sh (run
# from sway/config at startup) only starts swayidle.service when it's
# absent. ekatva writes it too ("on" or "high").
STATE_DIR="$HOME/.local/state/jyoti"
STATE_FILE="$STATE_DIR/enabled"
mkdir -p "$STATE_DIR"

# candy-icons has no "awake" icon; the screensaver one is this toggle's real
# mechanism (the idle system). The title says which way it went.
ICON=/usr/share/icons/candy-icons/apps/scalable/preferences-desktop-screensaver.svg
EKATVA="$HOME/.local/bin/ekatva"

MODE=${1:-toggle}
case "$MODE" in toggle|off|switch|akhanda|nandadipa) ;; *) echo "usage: jyoti-toggle.sh [toggle|off|switch|akhanda|nandadipa]" >&2; exit 2 ;; esac

nanda_msg() { notify-send -i "$ICON" "Jyoti: Nandādīpa" "The lamp kept burning day and night: awake, and running even with the lid closed"; }
on_msg() { notify-send -i "$ICON" "Jyoti: Akhaṇḍa" "The unbroken flame: the laptop stays awake, no dimming, lock or sleep until you turn this off"; }
off_msg() { notify-send -i "$ICON" "Jyoti: Śānta" "The screen dims, locks and sleeps normally again"; }

ekatva_up() {
    [ -x "$EKATVA" ] && [ -S "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/ekatva.sock" ] &&
        now=$("$EKATVA" jyoti 2>/dev/null)
}

if ekatva_up; then
    # "jyoti: shanta", "jyoti: akhanda", "jyoti: nandadipa until …"
    case "$MODE:$now" in
        off:*) "$EKATVA" jyoti shanta >/dev/null && off_msg ;;
        akhanda:*": akhanda"* | nandadipa:*": nandadipa"*) ;;  # already there
        akhanda:*) "$EKATVA" jyoti akhanda >/dev/null && on_msg ;;
        nandadipa:*) "$EKATVA" jyoti nandadipa >/dev/null && nanda_msg ;;
        switch:*": nandadipa"*) "$EKATVA" jyoti akhanda >/dev/null && on_msg ;;
        switch:*": shanta"* | switch:*": off"*) ;;  # nothing lit to switch
        switch:*) "$EKATVA" jyoti nandadipa >/dev/null && nanda_msg ;;
        toggle:*": shanta"* | toggle:*": off"*) "$EKATVA" jyoti akhanda >/dev/null && on_msg ;;
        toggle:*) "$EKATVA" jyoti shanta >/dev/null && off_msg ;;
    esac
elif [ "$MODE" = switch ] || [ "$MODE" = nandadipa ]; then
    notify-send -i "$ICON" "Jyoti: Nandādīpa needs ekatva" "Staying awake with the lid closed is held by ekatva. Turn ekatva on (quick settings), then right-click again"
elif [ "$MODE" != off ] && systemctl --user is-active --quiet swayidle.service; then
    # toggle or akhanda, from Śānta
    systemctl --user stop swayidle.service && touch "$STATE_FILE" && on_msg
elif [ "$MODE" != akhanda ] && ! systemctl --user is-active --quiet swayidle.service; then
    # The marker goes only once swayidle really runs again: where the user's
    # systemd can't be reached (a test session, a broken bus) "not active"
    # is only a failed question, and removing it there put a lit Jyoti out
    # in the bar (2026-11-28).
    systemctl --user start swayidle.service && rm -f "$STATE_FILE" && off_msg
fi

# Refresh the waybar capsule now (bar-events.py also sees swayidle's state
# change, 0.3 s later).
"$HOME/.local/bin/waybar-signal" 12 2>/dev/null || true
