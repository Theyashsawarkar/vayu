#!/bin/bash
# Volume OSD helper: adjusts, or toggles mute on, the default sink, then
# fires a progress-bar-style mako notification. Used by both the
# XF86Audio* keybindings and the waybar pulseaudio module (click/scroll).
#
# This can fire in rapid bursts (e.g. a touchpad's smooth-scroll deltas
# outrunning waybar's smooth-scrolling-threshold debounce) -- confirmed by
# forcing 30 concurrent "+5%" calls, which raced pactl's own relative-volume
# math and drove the sink to 1494%. Two defenses against that:
#   1. flock serializes read-current -> compute-target -> apply, so
#      concurrent calls stack correctly instead of racing on a stale read.
#   2. The target is clamped to 0-100 ourselves -- pactl's relative "+N%"
#      does NOT clamp on its own, so without this a burst can genuinely
#      overdrive well past 100%.
LOCK="/tmp/volume_osd.lock"

# Same tiering convention as waybar's own battery icons elsewhere in this
# desktop (different icon per range, not one static speaker glyph).
#
# Absolute paths, not theme names -- see brightness_osd.sh for the full
# story: mako has no GTK-style theme resolution. candy-icons (Papirus's
# replacement) ships these same four under `status/scalable`, real,
# hardcoded-fill (confirmed `grep -c currentColor` is 0 on all four
# before using them) -- scalable SVGs this time rather than a fixed
# 32x32 raster, so no size tradeoff versus this repo's other 48x48
# notification icons.
volume_icon() {
    local pct="$1"
    if [ "$pct" -eq 0 ]; then
        echo "/usr/share/icons/candy-icons/status/scalable/audio-volume-muted.svg"
    elif [ "$pct" -lt 34 ]; then
        echo "/usr/share/icons/candy-icons/status/scalable/audio-volume-low.svg"
    elif [ "$pct" -lt 67 ]; then
        echo "/usr/share/icons/candy-icons/status/scalable/audio-volume-medium.svg"
    else
        echo "/usr/share/icons/candy-icons/status/scalable/audio-volume-high.svg"
    fi
}

adjust_volume() {
    # $1 like "+5%" or "-5%" (as passed by sway/waybar bindings)
    (
        flock -x 9
        current=$(pactl get-sink-volume @DEFAULT_SINK@ | grep -Po '\d+(?=%)' | head -n 1)
        [ -z "$current" ] && current=100
        delta="${1%%%}"
        delta="${delta#+}"
        target=$((current + delta))
        [ "$target" -lt 0 ] && target=0
        [ "$target" -gt 100 ] && target=100
        pactl set-sink-volume @DEFAULT_SINK@ "${target}%"
        # Scrolling/pressing down to exactly 0% also sets the real
        # PulseAudio mute flag now, not just the number -- 0% and muted
        # are the same silence to the ear, so make them the same state,
        # not two states that happen to sound identical. This is also
        # the only reliable way waybar's own bar icon shows a muted
        # look at 0%: tried giving format-icons its own 0%-only
        # threshold entry first ({"icon":...,"max":0}), documented as
        # supported in waybar's own man page and source -- confirmed
        # directly, ASCII-dumping the actual rendered pixels rather than
        # trusting color-based sampling again after it misled the
        # previous two attempts, that this waybar build (v0.15.0) simply
        # doesn't render *any* icon via that threshold-object form for
        # the regular (non-muted) format string, even though the plain
        # array it replaced worked fine -- a real bug/incompatibility in
        # this specific version, not a config mistake. This sidesteps it
        # entirely by reusing format-muted, which was already proven
        # working the whole time.
        if [ "$target" -eq 0 ]; then
            pactl set-sink-mute @DEFAULT_SINK@ 1
        else
            pactl set-sink-mute @DEFAULT_SINK@ 0
        fi
    ) 9>"$LOCK"
}

if [ "$1" = "mute-toggle" ]; then
    pactl set-sink-mute @DEFAULT_SINK@ toggle
    if pactl get-sink-mute @DEFAULT_SINK@ | grep -q yes; then
        notify-send -h string:x-canonical-private-synchronous:sys-notify -u low -i "$(volume_icon 0)" "Volume" "Muted"
    else
        percentage=$(pactl get-sink-volume @DEFAULT_SINK@ | grep -Po '\d+(?=%)' | head -n 1)
        [ -n "$percentage" ] && notify-send -h string:x-canonical-private-synchronous:sys-notify -u low -h int:value:"$percentage" -i "$(volume_icon "$percentage")" "Volume" "${percentage}%"
    fi
    exit 0
fi

# Raising/lowering should always be audible, so drop mute first.
pactl set-sink-mute @DEFAULT_SINK@ 0

adjust_volume "$1"

# Extract the new volume percentage
percentage=$(pactl get-sink-volume @DEFAULT_SINK@ | grep -Po '\d+(?=%)' | head -n 1)

# Fire the notification with a progress bar
[ -n "$percentage" ] && notify-send -h string:x-canonical-private-synchronous:sys-notify -u low -h int:value:"$percentage" -i "$(volume_icon "$percentage")" "Volume" "${percentage}%"
