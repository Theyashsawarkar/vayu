#!/usr/bin/env bash
# Phone (KDE Connect) segment for waybar, JSON like docker-status.sh.
#   connected:    phone glyph + battery %, with a bolt while charging
#   disconnected: dim phone glyph (paired phone not reachable, or none paired)
# Click opens phone-picker.py. Reads the daemon's D-Bus state only -- never
# starts anything (the systemd unit kdeconnect.service owns the daemon).

ICON=$'\U000F011C'   # nf-md-cellphone
BOLT=$'\U000F140B'   # nf-md-lightning_bolt
BUS=org.kde.kdeconnect

get() {  # get <device-path> <iface> <prop> -> value (booleans/ints unquoted)
  busctl --user --auto-start=no get-property "$BUS" "$1" "$2" "$3" 2>/dev/null | cut -d' ' -f2- | tr -d '"'
}

name="" charge="" charging=""
# Only look if the daemon is already running: a call to a stopped
# kdeconnectd would D-Bus-activate it (`busctl tree` even with
# --auto-start=no), restarting a deliberately stopped daemon every 10 s.
# NameHasOwner asks the bus itself.
running=$(busctl --user call org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus NameHasOwner s "$BUS" 2>/dev/null)
# Paired device ids from the daemon's own `devices` method (onlyReachable=
# false, onlyPaired=true), not `busctl tree`: introspecting kdeconnectd
# every 10 s also spammed its log ("Skipped method sendClipboard").
paired_ids=""
[ "$running" = "b true" ] && paired_ids=$(busctl --user --auto-start=no call "$BUS" /modules/kdeconnect \
  org.kde.kdeconnect.daemon devices bb false true 2>/dev/null | grep -o '"[^"]*"' | tr -d '"')
# A phone asking to pair (it isn't paired yet, so it's not in $paired_ids).
requests=""
[ "$running" = "b true" ] && requests=$(busctl --user --auto-start=no get-property "$BUS" /modules/kdeconnect \
  org.kde.kdeconnect.daemon pairingRequests 2>/dev/null | grep -o '"[^"]*"' | tr -d '"')
if [ -n "$requests" ]; then
  req_name=$(get "/modules/kdeconnect/devices/${requests%% *}" org.kde.kdeconnect.device name)
  printf '{"text":"%s","class":"request","tooltip":"%s"}\n' \
    "<span color='#F9E2AF'>$ICON</span>  <span color='#F9E2AF'>pair?</span>" \
    "$req_name wants to pair\nClick: phone picker (Accept / Reject)"
  exit 0
fi
for id in $paired_ids; do
  path=/modules/kdeconnect/devices/$id
  [ "$(get "$path" org.kde.kdeconnect.device isPaired)" = true ] || continue
  [ "$(get "$path" org.kde.kdeconnect.device isReachable)" = true ] || { paired_name=$(get "$path" org.kde.kdeconnect.device name); continue; }
  name=$(get "$path" org.kde.kdeconnect.device name)
  charge=$(get "$path/battery" org.kde.kdeconnect.device.battery charge)
  charging=$(get "$path/battery" org.kde.kdeconnect.device.battery isCharging)
  break
done

if [ -n "$name" ]; then
  bat=""
  [ -n "$charge" ] && [ "$charge" -ge 0 ] 2>/dev/null && bat="  <span color='#CDD6F4'>${charge}%</span>"
  [ "$charging" = true ] && bat="$bat <span color='#F9E2AF'>$BOLT</span>"
  text="<span color='#89DCEB'>$ICON</span>$bat"
  tooltip="$name connected${charge:+, battery ${charge}%}$([ "$charging" = true ] && echo ', charging')\nClick: phone picker"
  class=connected
else
  text="<span color='#585B70'>$ICON</span>"
  tooltip="${paired_name:+$paired_name: }no phone connected (open KDE Connect on it, same network)\nClick: phone picker"
  class=disconnected
fi
printf '{"text":"%s","class":"%s","tooltip":"%s"}\n' "$text" "$class" "$tooltip"
