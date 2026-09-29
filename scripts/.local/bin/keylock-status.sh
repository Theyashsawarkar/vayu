#!/usr/bin/env bash
# Reports capslock/numlock state for waybar as JSON (same {text,class,tooltip}
# pattern as caffeine-status.sh/docker-status.sh). Takes "capslock" or
# "numlock" as $1 -- one script, two custom waybar modules, rather than
# duplicating this per key.
#
# Replaces waybar's built-in `keyboard-state` module -- that module has no
# on-click, no tooltip, and no cursor change at all (confirmed: none of those
# are in its documented config schema, man waybar-keyboard-state), so it
# can't be made clickable/hoverable no matter what CSS is thrown at it. A
# custom module can do all three.
#
# Reads the real kernel LED state directly (same source waybar's own
# built-in module reads via libevdev) rather than trusting any cached/
# derived state -- this is genuinely live.
#
# Empty "text" when unlocked is deliberate: paired with "hide-empty-text":
# true in the module's own waybar config, this makes the whole module
# disappear -- no space reserved at all -- rather than sitting there
# showing a dim "off" icon. Each module only reads its own key's LED, so
# capslock/numlock show/hide completely independently of each other.
set -uo pipefail

KEY="${1:?usage: keylock-status.sh capslock|numlock}"

case "$KEY" in
    capslock) LED_GLOB="/sys/class/leds/*::capslock/brightness"; LABEL="Caps Lock"; ICON=$'\uf023'; BADGE="A" ;;
    numlock)  LED_GLOB="/sys/class/leds/*::numlock/brightness";  LABEL="Num Lock";  ICON=$'\uf023'; BADGE="#" ;;
    *) echo "unknown key: $KEY" >&2; exit 1 ;;
esac

# Glob and read in bash, no ls/head/cat: waybar runs this on every
# Caps/Num Lock release (signal) plus a 30 s fallback poll.
LED_FILES=($LED_GLOB)
LED_FILE=${LED_FILES[0]}
if [ ! -e "$LED_FILE" ]; then
    # Genuine error (no LED device found at all) -- surfaced, not hidden,
    # so a real problem doesn't just silently disappear the same way the
    # normal "off" state now does.
    printf '{"text":"%s ?","class":"unlocked","tooltip":"%s: unknown (no LED device found)"}\n' "$BADGE" "$LABEL"
    exit 0
fi

read -r STATE < "$LED_FILE" 2>/dev/null || STATE=0

if [ "$STATE" -gt 0 ]; then
    printf '{"text":"%s %s","class":"locked","tooltip":"%s: On -- click to turn off"}\n' "$BADGE" "$ICON" "$LABEL"
else
    printf '{"text":"","class":"unlocked","tooltip":"%s: Off -- click to turn on"}\n' "$LABEL"
fi
