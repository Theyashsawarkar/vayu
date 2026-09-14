#!/usr/bin/env bash
# Toggles "caffeine mode" by stopping/starting the swayidle user service
# entirely -- no dpms-off, no lock, no suspend while it's stopped.
#
# Deliberately stops swayidle rather than just inhibiting suspend:
# systemd-inhibit-style suspend blocking wouldn't touch
# 'timeout 600 swaymsg output * dpms off' at all, since that's swayidle
# talking to sway directly, never going through logind. Stopping the
# service is the only thing that keeps the screen itself on too.
#
# Uses systemctl --user rather than raw process management (pkill/setsid)
# -- simpler and more reliable than juggling backgrounding/disown by hand.
#
# STATE_FILE persists the on/off choice across reboots -- swayidle.service
# is `enabled` (WantedBy=default.target), so systemd auto-starts it at
# every login on its own regardless of what this script did last;
# swayidle-startup.sh (run from sway/config at startup) reads this same
# file to re-apply whatever was chosen here, rather than caffeine mode
# silently resetting to off on every reboot.
STATE_DIR="$HOME/.local/state/caffeine"
STATE_FILE="$STATE_DIR/enabled"
mkdir -p "$STATE_DIR"

# Real bug, reported directly: the old weather icons (clouds-night /
# clear-day) are the exact same sun/moon iconography theme-toggle.sh's
# own notifications use for light/dark mode -- visually indistinguishable
# from a glance, so this notification read as "another theme toggle" at
# a glance instead of "caffeine". Papirus's own dedicated caffeine-cup
# icon was the fix at the time; candy-icons (Papirus's replacement) has
# no caffeine/coffee-cup icon of any kind (confirmed with `find`) --
# preferences-desktop-screensaver is the closest real concept it does
# ship (this toggle's actual mechanism is stopping/starting swayidle,
# i.e. the screensaver/idle system, so it's a legitimate match, not an
# arbitrary stand-in), confirmed no currentColor before using it. It has
# no natural on/off pair either, so it's used for both states here; the
# notification's own title text ("Caffeine on"/"Caffeine off") is what
# actually distinguishes them, the same way most apps that reuse one tray
# icon for a toggle rely on accompanying text or a separate visual state
# (waybar's own custom/caffeine module already handles the at-a-glance
# on/off distinction via its active/inactive CSS classes, not this
# notification).
ICON=/usr/share/icons/candy-icons/apps/scalable/preferences-desktop-screensaver.svg

if systemctl --user is-active --quiet swayidle.service; then
    systemctl --user stop swayidle.service
    touch "$STATE_FILE"
    notify-send -i "$ICON" "Caffeine on" "Screen will stay on, laptop won't sleep or lock until you turn this off"
else
    systemctl --user start swayidle.service
    rm -f "$STATE_FILE"
    notify-send -i "$ICON" "Caffeine off" "Screen will dim, lock, and suspend normally again"
fi
