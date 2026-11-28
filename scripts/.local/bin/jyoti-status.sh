#!/usr/bin/env bash
# Reports jyoti (ज्योति: keeping the laptop awake; see jyoti-toggle.sh) for
# waybar. It's lit precisely when swayidle.service is stopped. JSON output
# so waybar can style each level by its CSS class:
#   inactive  off: hidden (no lamp; quick settings has the toggle)
#   active    Akhaṇḍa, the unbroken flame: no dimming, lock or sleep
#             (the diya, in blue)
#   strong    Nandādīpa, the lamp kept burning day and night: Akhaṇḍa, and
#             the laptop keeps running with the lid closed (the samai, in
#             ember). ekatva writes "high" into the state file;
#             jyoti-toggle.sh without ekatva leaves it empty: Akhaṇḍa.
# The lamp itself is a picture (style.css: jyoti-akhanda.svg,
# jyoti-nandadipa.svg, the same drawings as ekatva's phone app and popup);
# the text is only a space for it to sit in.

LAMP=$'  '
# With ekatva running, its own saved state says the level (it is what holds
# the block). The marker file can be lost (2026-11-28: a test run with the
# real home deleted it, and Nandādīpa showed as Akhaṇḍa); ekatva's changes
# only when the level does. Without ekatva: swayidle and the marker file.
STATE="${XDG_STATE_HOME:-$HOME/.local/state}"
STATE_FILE="$STATE/jyoti/enabled"
EKATVA_STATE="$STATE/ekatva/jyoti.json"
SOCK="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/ekatva.sock"

level=
if [ -S "$SOCK" ] && [ -r "$EKATVA_STATE" ]; then
    level=$(grep -o '"level":"[a-z]*"' "$EKATVA_STATE" | cut -d'"' -f4)
fi
if [ -z "$level" ]; then
    if systemctl --user is-active --quiet swayidle.service; then level=off
    elif [ "$(head -c 8 "$STATE_FILE" 2>/dev/null | tr -d '[:space:]')" = high ]; then level=high
    else level=on
    fi
fi

if [ "$level" = off ]; then
    printf '{"text":"","class":"inactive","tooltip":"<b>Jyoti</b>  Śānta"}\n'
elif [ "$level" = high ]; then
    printf '{"text":"%s","class":"strong","tooltip":"<b>Jyoti</b>  Nandādīpa\\nAwake, even with the lid closed\\n<span size=\\"small\\" alpha=\\"60%%\\">Click: put it out  ·  Right-click: Akhaṇḍa</span>"}\n' "$LAMP"
else
    printf '{"text":"%s","class":"active","tooltip":"<b>Jyoti</b>  Akhaṇḍa\\nNo dimming, lock or sleep\\n<span size=\\"small\\" alpha=\\"60%%\\">Click: put it out  ·  Right-click: Nandādīpa</span>"}\n' "$LAMP"
fi
