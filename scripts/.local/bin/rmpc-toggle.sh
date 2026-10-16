#!/usr/bin/env bash
# Toggles rmpc's floating window open/hidden via sway's scratchpad --
# not process-kill-based like toggle-popup.sh, deliberately: scratchpad
# show/hide is purely a window-visibility operation, it never touches
# the underlying process, and playback lives in mpd.service (a real,
# independent systemd --user daemon) regardless of whether rmpc's own
# window is open at all -- closing rmpc entirely wouldn't even stop
# playback, let alone just hiding it.
#
# First launch: no window exists yet -- start it, and the for_window
# rule in sway/config (floating + sized + centered + moved into the
# scratchpad, shown immediately) handles making it appear correctly.
# Every press after that: the window already exists, so just toggle its
# scratchpad visibility -- verified directly (on this same pattern, for
# termusic before it) that `scratchpad show` on a window already shown
# from the scratchpad hides it again, not a no-op.
set -uo pipefail

# rmpc finds MPD's socket through MPD_HOST (see rmpc's config.ron);
# normally inherited from ~/.profile, this covers a session without it.
export MPD_HOST="${MPD_HOST:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/mpd/socket}"

if pgrep -x rmpc >/dev/null; then
    swaymsg '[app_id="^rmpc$"] scratchpad show' >/dev/null
else
    # setsid + redirected stdio -- without this, kitty inherits this
    # script's own stdout/stderr, and whatever launched this script (a
    # sway `exec`, a shell) can end up blocking on those file
    # descriptors staying open for as long as kitty runs, rather than
    # returning immediately the way a background launch should.
    #
    # No per-window opacity override here (there was one, briefly:
    # -o background_opacity=0.3, tuned before real blur was wired in --
    # removed once blur made it unnecessary, see below). Runs at kitty's
    # own global background_opacity 0.85 (kitty/kitty.conf), same as
    # every other terminal window.
    #
    # The actual "glass" look comes from real compositor-level blur now
    # (`blur enable`, sway/config's own rmpc for_window rule), not from
    # opacity tuning -- worth recording since an earlier pass chased the
    # wrong variable first. Before blur was added, lowering opacity was
    # the only lever available, and pushing it down to 0.3 did produce a
    # measurable, verified pixel shift -- but what actually showed
    # through at low opacity was the wallpaper completely SHARP and
    # unblurred, which reads as "see-through window", not glass. wofi's
    # own real glass panel (wofi/style.css) runs at 0.85 alpha, not
    # something low -- paired with real blur (layer_effects "wofi" in
    # sway/config), that's what a frosted-glass panel actually looks
    # like: mostly opaque, with a blurred (not sharp) wallpaper hint
    # behind it. Matched that same ratio here instead of re-deriving a
    # new one: kitty's global 0.85 was already correct, blur was the
    # missing piece, not opacity.
    #
    # -o "map escape launch ..." rebinds Escape for THIS kitty instance
    # only (kitty/kitty.conf's own global map table is untouched) to run
    # rmpc-hide.sh instead of passing the key through to rmpc's own pty --
    # makes Escape hide the whole popup, matching every other popup in
    # this desktop (wofi's are native, nwg-bar's is native, this one
    # wasn't). See rmpc-hide.sh's own comment for why a separate script
    # instead of inlining the swaymsg call here, and for the tradeoff
    # this makes with rmpc's own internal Esc-bound `Close` action.
    setsid kitty --class rmpc \
        -o "map escape launch --type=background $HOME/.local/bin/rmpc-hide.sh" \
        -e rmpc >/dev/null 2>&1 &
fi
