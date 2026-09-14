#!/usr/bin/env bash
# Toggles between light and dark mode for every app that reads the
# standard GNOME/GTK dconf keys (gtk-theme, color-scheme, icon-theme) --
# the vast majority of regular GUI apps (file managers, browsers' GTK
# chrome, settings dialogs, GTK-based editors) detect and follow this
# automatically, which is the actual mechanism behind "apps detect OS
# dark mode".
#
# Verified end to end, not assumed: dconf write -> the XDG Desktop Portal
# (org.freedesktop.portal.Desktop, backed by xdg-desktop-portal-gtk per
# /usr/share/xdg-desktop-portal/sway-portals.conf's "default=gtk" for the
# Settings interface) reflects the new value immediately on
# Settings.Read, AND actually emits a live SettingChanged signal on both
# the legacy org.gnome.desktop.interface namespace and the newer
# org.freedesktop.appearance one (confirmed with `gdbus monitor` while
# running this script -- both fired with the correct new value, not just
# assumed from the spec).
#
# Real bug found and fixed here: this used to write gtk-theme/icon-theme
# names unconditionally, including for the light palette
# (catppuccin-latte-mauve-standard+default) before those packages were
# actually confirmed installed on this machine (checked:
# `pacman -Q catppuccin-gtk-theme-latte` failed -- packages/aur.txt lists
# it, but the handed-off install command hadn't been run yet). Writing
# a theme/icon-theme name that doesn't resolve to anything installed
# doesn't fail loudly -- native GTK apps just silently keep rendering
# whatever they last successfully loaded, which looks exactly like "the
# toggle did nothing" even though color-scheme itself changed correctly.
# Now checks /usr/share/themes and /usr/share/icons directly before
# writing either key, and skips it (leaving the previous, working value
# in place) with a clear notification if the target isn't actually
# installed -- color-scheme is always written regardless, since it's a
# pure preference value with no file dependency, and is the one signal
# apps like Firefox/Zen actually need for their own internal dark/light
# CSS switching (they don't render using arbitrary system GTK theme
# files the way a native GTK app does).
#
# Also worth knowing, and not something this or any script can fix: an
# app has to actually be listening for org.freedesktop.appearance's
# SettingChanged signal for a *live* switch with no restart -- confirmed
# real and firing correctly here, but whether a given app subscribes to
# it is up to that app. Firefox-based browsers specifically have a
# widget.use-xdg-desktop-portal.settings preference (about:config) gating
# whether they use the portal for this at all; if a browser stays on its
# last-detected appearance after a toggle, checking that preference is
# the first thing to look at -- outside what any desktop-side config can
# reach into.
#
# Deliberately does NOT touch this desktop's own bar/launcher/
# notification styling (waybar/wofi/mako's style.css, sway's window
# border colors) -- those are hand-built throughout this whole repo to
# one specific Catppuccin Mocha palette, a deliberate aesthetic choice,
# not something meant to flip with a generic light/dark toggle.
set -uo pipefail

DCONF_IFACE=/org/gnome/desktop/interface

theme_exists() {
    [ -d "/usr/share/themes/$1" ]
}

icon_theme_exists() {
    [ -d "/usr/share/icons/$1" ]
}

apply_gtk_theme() {
    local name="$1"
    if theme_exists "$name"; then
        dconf write "$DCONF_IFACE/gtk-theme" "'$name'"
    else
        echo "gtk-theme '$name' not installed under /usr/share/themes -- left unchanged" >&2
        return 1
    fi
}

apply_icon_theme() {
    local name="$1"
    if icon_theme_exists "$name"; then
        dconf write "$DCONF_IFACE/icon-theme" "'$name'"
    else
        echo "icon-theme '$name' not installed under /usr/share/icons -- left unchanged" >&2
        return 1
    fi
}

scheme=$(dconf read "$DCONF_IFACE/color-scheme" 2>/dev/null | tr -d "'")
missing=""

if [ "$scheme" = "prefer-light" ]; then
    dconf write "$DCONF_IFACE/color-scheme" "'prefer-dark'"
    apply_gtk_theme "catppuccin-mocha-mauve-standard+default" || missing="${missing}GTK theme, "
    # candy-icons (Papirus's replacement) has no separate light/dark
    # variant -- unlike Papirus-Dark/-Light, one icon-theme name covers
    # both palettes, so this call is really just a re-confirmation that
    # it's still installed, not an actual switch.
    apply_icon_theme "candy-icons" || missing="${missing}icon theme, "
    label="dark"
    # Absolute path, not a theme name -- mako has no GTK-style theme
    # resolution. candy-icons ships no weather icons at all (confirmed
    # with `find`), so this falls back to AdwaitaLegacy's real-fill
    # weather-clear-night.png instead of a `fill:currentColor` symbolic
    # icon, which would go near-invisible on this desktop's dark
    # notification background (see brightness_osd.sh / mako/config for
    # the full story).
    icon="/usr/share/icons/AdwaitaLegacy/48x48/legacy/weather-clear-night.png"
else
    dconf write "$DCONF_IFACE/color-scheme" "'prefer-light'"
    apply_gtk_theme "catppuccin-latte-mauve-standard+default" || missing="${missing}GTK theme, "
    apply_icon_theme "candy-icons" || missing="${missing}icon theme, "
    label="light"
    icon="/usr/share/icons/AdwaitaLegacy/48x48/legacy/weather-clear.png"
fi

if [ -n "$missing" ]; then
    notify-send -u normal -i "$icon" "Theme" \
        "Switched to $label mode (${missing%, } not installed yet -- run the install command from CHANGELOG.md)"
else
    notify-send -u low -i "$icon" "Theme" "Switched to $label mode"
fi
