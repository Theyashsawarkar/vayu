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
STATE_FILE="$HOME/.local/state/jyoti/enabled"

if systemctl --user is-active --quiet swayidle.service; then
    printf '{"text":"","class":"inactive","tooltip":"Jyoti: Śānta"}\n'
elif [ "$(head -c 8 "$STATE_FILE" 2>/dev/null | tr -d '[:space:]')" = high ]; then
    printf '{"text":"%s","class":"strong","tooltip":"Jyoti: Nandādīpa -- awake even with the lid closed. Click to let it sleep again"}\n' "$LAMP"
else
    printf '{"text":"%s","class":"active","tooltip":"Jyoti: Akhaṇḍa -- no dimming, lock or sleep. Click to let it sleep again"}\n' "$LAMP"
fi
