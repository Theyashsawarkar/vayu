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

on_msg() { notify-send -i "$ICON" "Jyoti: Akhaṇḍa" "The unbroken flame: the laptop stays awake, no dimming, lock or sleep until you turn this off"; }
off_msg() { notify-send -i "$ICON" "Jyoti: Śānta" "The screen dims, locks and sleeps normally again"; }

if [ -x "$EKATVA" ] && [ -S "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/ekatva.sock" ] &&
    now=$("$EKATVA" jyoti 2>/dev/null); then
    # "jyoti: shanta", "jyoti: akhanda", "jyoti: nandadipa until …"
    case "$now" in
        *": shanta"* | *": off"*) "$EKATVA" jyoti akhanda >/dev/null && on_msg ;;
        *) "$EKATVA" jyoti shanta >/dev/null && off_msg ;;
    esac
elif systemctl --user is-active --quiet swayidle.service; then
    systemctl --user stop swayidle.service
    touch "$STATE_FILE"
    on_msg
else
    systemctl --user start swayidle.service
    rm -f "$STATE_FILE"
    off_msg
fi

# Refresh the waybar capsule now (bar-events.py also sees swayidle's state
# change, 0.3 s later).
"$HOME/.local/bin/waybar-signal" 12 2>/dev/null || true
