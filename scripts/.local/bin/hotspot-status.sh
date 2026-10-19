#!/usr/bin/env bash
# Hotspot segment for waybar (custom/hotspot), JSON like phone-status.sh.
#   on:  access-point glyph + how many devices are connected, teal border;
#        the tooltip has the name, password, devices and internet source
#   off: nothing (waybar hides an empty module)
# Click opens the hotspot panel (vyom tarang hotspot), right click turns
# it off. Refreshed by bar-events.py (signal 15) when NetworkManager's
# active connections change or a device joins or leaves (`iw event`), and
# every 30 s for devices that vanish without leaving (off is one nmcli call).
ICON=$'\U000F0003'   # nf-md-access_point_network
# waybar runs this without the login shell's PATH (vayu-hotspot lives here).
PATH=$HOME/.local/bin:$PATH

# Cheap first: one nmcli call, and nothing more while it's off.
nmcli -t -f NAME connection show --active 2>/dev/null | grep -qxF "Vayu Hotspot" || { echo '{"text": "", "class": "off"}'; exit 0; }

s=$(vayu-hotspot status --json 2>/dev/null) || { echo '{"text": "", "class": "off"}'; exit 0; }
jq -c --arg icon "$ICON" '
  ([.clients[] | "  " + (if .name != "" then .name else "unknown device" end) + "  " + .ip] | join("\n")) as $devs
  | {text: "\($icon)  \(.client_count)",
     class: "on",
     tooltip: ("Hotspot \"\(.ssid)\" (\(.band))\nPassword: \(.password)\nInternet: \(if .internet == "" then "none (plug in ethernet)" else .internet end)\n"
               + (if .client_count == 0 then "No devices connected" else "\(.client_count) connected:\n" + $devs end)
               + "\n\nClick: hotspot panel · Right click: turn off")}' <<<"$s"
