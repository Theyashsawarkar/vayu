#!/usr/bin/env bash
# Phone (KDE Connect) segment for waybar, JSON like docker-status.sh.
#   connected:    phone glyph + battery %, with a bolt while charging
#   disconnected: hidden (paired phone not reachable, or none paired)
# Click opens the phone panel (vyom doot). Refreshed by bar-events.py on KDE Connect
# signals (waybar signal 13), never on a timer. Reads the daemon's
# D-Bus state only -- never starts anything (the systemd unit
# kdeconnect.service owns the daemon).

# Colours from the current varna theme (palette.json), Vayu's own without it.
PALETTE=${XDG_STATE_HOME:-$HOME/.local/state}/varna/palette.json
col() { local v; v=$(jq -r ".colors.$1 // empty" "$PALETTE" 2>/dev/null); echo "${v:-$2}"; }
# waybar's JSON, built by jq (a phone name with " or \ broke printf'd JSON),
# the tooltip escaped for Pango (a name with & or < broke the tooltip).
# (\& : in bash 5.2 a bare & in the replacement means "the match".)
esc() { local s=${1//&/\&amp;}; s=${s//</\&lt;}; printf '%s' "${s//>/\&gt;}"; }
emit() { jq -cn --arg text "$1" --arg class "$2" --arg tooltip "$(esc "$3")" '{text: $text, class: $class, tooltip: $tooltip}'; }

ICON=$'\U000F011C'   # nf-md-cellphone
BOLT=$'\U000F140B'   # nf-md-lightning_bolt
BUS=org.kde.kdeconnect

# Parsing stays in bash: this runs from waybar, and the old
# `busctl | cut | tr` per property launched 32 processes a run. Now it's
# one busctl per call, several properties per get-property.
props() {  # props <path> <iface> <prop>... -> PROPS[], values unquoted
  local out
  out=$(busctl --user --auto-start=no get-property "$BUS" "$@" 2>/dev/null)
  mapfile -t PROPS <<< "$out"
  PROPS=("${PROPS[@]#* }"); PROPS=("${PROPS[@]//\"/}")
}
strings() {  # strings <busctl "as N \"a\" \"b\"" output> -> STRINGS[]
  local s=$1 re='"([^"]*)"'
  STRINGS=()
  while [[ $s =~ $re ]]; do STRINGS+=("${BASH_REMATCH[1]}"); s=${s#*"${BASH_REMATCH[0]}"}; done
}

name="" charge="" charging="" paired_name=""
# Only look if the daemon is already running: a call to a stopped
# kdeconnectd would D-Bus-activate it (`busctl tree` even with
# --auto-start=no), restarting a deliberately stopped daemon on every run.
# NameHasOwner asks the bus itself.
running=$(busctl --user call org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus NameHasOwner s "$BUS" 2>/dev/null)
# Paired device ids from the daemon's own `devices` method (onlyReachable=
# false, onlyPaired=true), not `busctl tree`: introspecting kdeconnectd
# on every run also spammed its log ("Skipped method sendClipboard").
paired_ids=() requests=()
if [ "$running" = "b true" ]; then
  strings "$(busctl --user --auto-start=no call "$BUS" /modules/kdeconnect \
    org.kde.kdeconnect.daemon devices bb false true 2>/dev/null)"
  paired_ids=("${STRINGS[@]}")
  # A phone asking to pair (it isn't paired yet, so it's not in paired_ids).
  strings "$(busctl --user --auto-start=no get-property "$BUS" /modules/kdeconnect \
    org.kde.kdeconnect.daemon pairingRequests 2>/dev/null)"
  requests=("${STRINGS[@]}")
fi
if [ ${#requests[@]} -gt 0 ]; then
  props "/modules/kdeconnect/devices/${requests[0]}" org.kde.kdeconnect.device name
  emit "<span color='$(col warn '#F9E2AF')'>$ICON</span>  <span color='$(col warn '#F9E2AF')'>pair?</span>" request \
    "${PROPS[0]} wants to pair"$'\n'"Click: phone picker (Accept / Reject)"
  exit 0
fi
for id in "${paired_ids[@]}"; do
  path=/modules/kdeconnect/devices/$id
  props "$path" org.kde.kdeconnect.device name isPaired isReachable
  [ "${PROPS[1]}" = true ] || continue
  [ "${PROPS[2]}" = true ] || { paired_name=${PROPS[0]}; continue; }
  name=${PROPS[0]}
  props "$path/battery" org.kde.kdeconnect.device.battery charge isCharging
  charge=${PROPS[0]} charging=${PROPS[1]}
  break
done

if [ -n "$name" ]; then
  bat=""
  [ -n "$charge" ] && [ "$charge" -ge 0 ] 2>/dev/null && bat="  <span color='$(col fg '#CDD6F4')'>${charge}%</span>"
  [ "$charging" = true ] && bat="$bat <span color='$(col warn '#F9E2AF')'>$BOLT</span>"
  text="<span color='$(col sky '#89DCEB')'>$ICON</span>$bat"
  tooltip="$name connected${charge:+, battery ${charge}%}$([ "$charging" = true ] && echo ', charging')"$'\n'"Click: phone picker"
  class=connected
else
  # Not connected: nothing on the bar (it's an "only while on" indicator;
  # Super+Shift+o still opens the phone picker).
  text=""
  tooltip="${paired_name:+$paired_name: }no phone connected"
  class=disconnected
fi
emit "$text" "$class" "$tooltip"
