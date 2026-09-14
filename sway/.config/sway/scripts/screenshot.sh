#!/bin/bash
# Usage:
#   screenshot.sh        → full screen (default, keeps Print key working)
#   screenshot.sh region → select area with slurp

MODE="${1:-full}"
DIR="$HOME/Pictures/Screenshots"
FILE="$DIR/$(date +'%Y-%m-%d_%H-%M-%S_screenshot.png')"

mkdir -p "$DIR"

# Real (absolute-path) icon, not a theme name -- see brightness_osd.sh for
# the full story on why mako needs this rather than a bare icon name.
# Neither process-stop nor any dialog-* icon exists anywhere in
# candy-icons at all (confirmed with `find` -- no `status` category
# dialogs shipped, unlike Papirus). AdwaitaLegacy's real-fill
# dialog-warning.png is the closest available real-fill match for "this
# got interrupted", not an error, not nothing either.
ICON_CANCELLED=/usr/share/icons/AdwaitaLegacy/48x48/legacy/dialog-warning.png

if [[ "$MODE" == "region" ]]; then
  GEOMETRY=$(slurp 2>/dev/null)
  if [[ -z "$GEOMETRY" ]]; then
    notify-send -u low -i "$ICON_CANCELLED" "Screenshot cancelled"
    exit 0
  fi
  grim -g "$GEOMETRY" "$FILE"
else
  grim "$FILE"
fi

wl-copy <"$FILE"
notify-send \
  -h string:x-canonical-private-synchronous:sys-notify \
  -i "$FILE" \
  "Screenshot captured" \
  "Saved and copied to clipboard."
