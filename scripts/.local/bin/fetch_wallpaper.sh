#!/usr/bin/env bash
# Fetches a new daily wallpaper, validates it, and applies it via sway.
#
# Designed to never leave sway without a usable background and never hand
# swaybg anything unvalidated: checks network connectivity first, retries the
# download, verifies the result is actually an image (not an API error page
# saved as .jpg), and falls back to the last known-good wallpaper -- or, if
# there isn't one yet, a plain solid color -- rather than ever applying
# something that could crash swaybg.
#
# Logs to $LOG_FILE (also visible via `journalctl --user -u wallpaper.service`
# when run from the timer). Also fires notify-send at the key points (start,
# success, fallback used, total failure) -- this used to be silent, log-file
# only, which was fine for the daily timer but meant a manual click (the
# waybar wallpaper-refresh icon) gave zero feedback that anything happened
# for the several seconds a real download takes.
#
# WALLPAPER_URL used to be one fixed URL (index=0, mkt=en-US) -- confirmed
# directly (curl'd it twice, compared md5sums: identical) that Bing's
# "wallpaper of the day" for a given index+market is genuinely static for
# the whole day, so every click within the same day fetched the exact same
# bytes no matter how many times you asked. Also confirmed `index` (0-7ish,
# recent past days) and `mkt` (country/locale) each independently vary the
# actual image -- different markets often get a different photo for the
# same day (tested en-US/de-DE/fr-FR shared one image, en-GB had a
# different one, ja-JP/zh-CN shared a third, all on the same real day).
# Now picks a random recent index and a random market on every run, so a
# click is genuinely likely to differ from the last one instead of being
# pinned to one fixed day+country.

set -uo pipefail
# Deliberately not `-e`: this script must always be able to reach its own
# fallback logic, never die partway through on an unexpected error.

BASE_DIR="$HOME/Pictures/Wallpapers"
ACTIVE_DIR="$BASE_DIR/Active"
ARCHIVE_DIR="$BASE_DIR/Archive"
CURRENT="$BASE_DIR/current.jpg"
LAST_GOOD="$BASE_DIR/.last_good.jpg"
LOCK_FILE="/tmp/fetch_wallpaper.lock"
LOG_DIR="$HOME/.local/state/fetch-wallpaper"
LOG_FILE="$LOG_DIR/fetch-wallpaper.log"
LOG_MAX_BYTES=1048576
MAX_ARCHIVE_FILES=60  # ~2 months of daily wallpapers before pruning oldest
FALLBACK_COLOR="1e1e2e"  # Catppuccin Mocha base -- last resort if there is no
                          # good wallpaper on disk at all (e.g. brand-new
                          # machine, first run ever, no network yet)

# Absolute paths, not theme names -- mako has no GTK-style theme
# resolution (see brightness_osd.sh / mako/config for the full story).
# preferences-desktop-wallpaper is candy-icons' own real-fill icon
# (Papirus's replacement, same name carried over); candy-icons ships no
# dialog-* icons at all though, so those two fall back to AdwaitaLegacy's
# real-fill equivalents instead.
ICON_WALLPAPER=/usr/share/icons/candy-icons/preferences/scalable/preferences-desktop-wallpaper.svg
ICON_WARNING=/usr/share/icons/AdwaitaLegacy/48x48/legacy/dialog-warning.png
ICON_ERROR=/usr/share/icons/AdwaitaLegacy/48x48/legacy/dialog-error.png
# Markets confirmed to actually exist for this API; not all of them are
# guaranteed to differ from each other on any given day (several share the
# same underlying photo, seen directly while testing), but spreading
# across this many real markets makes repeated fetches land on a
# genuinely different image far more often than not.
WALLPAPER_MARKETS=(en-US en-GB en-CA en-AU en-IN de-DE fr-FR fr-CA ja-JP zh-CN es-ES es-MX it-IT pt-BR ru-RU ko-KR nl-NL pl-PL tr-TR sv-SE)
# 0-3 = today through 3 days ago -- stays "recent", not reaching deep into
# Bing's archive, while still adding a second axis of variety alongside
# the market choice.
WALLPAPER_MAX_INDEX=3
MAX_RETRIES=3
RETRY_DELAY=5

wallpaper_url() {
  local idx="$1" mkt="$2"
  printf 'https://bing.biturl.top/?resolution=1920&format=image&index=%s&mkt=%s' "$idx" "$mkt"
}

mkdir -p "$ACTIVE_DIR" "$ARCHIVE_DIR" "$LOG_DIR"

log() {
  local level="$1"; shift
  printf '[%s] [%s] %s\n' "$(date -Iseconds)" "$level" "$*" | tee -a "$LOG_FILE" >&2
}

# Simple size-based log rotation -- keep one previous log, nothing unbounded.
if [ -f "$LOG_FILE" ] && [ "$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)" -gt "$LOG_MAX_BYTES" ]; then
  mv -f "$LOG_FILE" "$LOG_FILE.old"
fi

# Don't let the timer and a manual run stomp on each other.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log INFO "another fetch_wallpaper.sh is already running, exiting"
  notify-send -u low -i "$ICON_WALLPAPER" "Wallpaper" "Already fetching one -- hang tight"
  exit 0
fi

notify-send -u low -i "$ICON_WALLPAPER" "Wallpaper" "Fetching a new one..."

is_valid_image() {
  local f="$1"
  [ -s "$f" ] || return 1
  case "$(file -b --mime-type "$f" 2>/dev/null)" in
    image/*) return 0 ;;
    *) return 1 ;;
  esac
}

apply_background() {
  # $1 = image|color, $2 = path or hex color
  #
  # wallpaper.service's timer has Persistent=true (catches up a missed
  # daily run on boot, systemd/.config/systemd/user/wallpaper.timer) --
  # but that only orders it after network-online.target, nothing ties it
  # to sway actually being up yet. systemd --user and sway can both start
  # around the same moment at login, and depending on graphical-session.target
  # for real ordering doesn't work here -- checked directly
  # (`systemctl --user status graphical-session.target`): it's a real
  # loaded unit, but stays "inactive (dead)" the whole session, since
  # nothing in this sway config ever activates it. So a boot-time catch-up
  # run can genuinely race sway's own startup and hit this function before
  # the IPC socket exists yet -- previously a single instant check, which
  # would silently give up and leave the *previous* wallpaper showing
  # (current.jpg was still updated on disk, just never told to sway live)
  # until the next manual reload, which doesn't happen on its own.
  # Retries for up to 20s instead of checking once -- comfortably covers
  # that startup race, and costs nothing in the normal case (manual click,
  # scheduled run well after login) where the socket is already there and
  # this returns on the very first check.
  local mode="$1" value="$2" swaysock=""
  for _ in $(seq 1 20); do
    swaysock=$(ls /run/user/"$(id -u)"/sway-ipc.*.sock 2>/dev/null | head -n1)
    [ -n "$swaysock" ] && break
    sleep 1
  done
  if [ -z "$swaysock" ]; then
    log WARN "no sway IPC socket found after waiting -- not applying live (sway's own 'output * bg' config line will use current.jpg on next start/reload)"
    return 1
  fi
  export SWAYSOCK="$swaysock"
  if [ "$mode" = "image" ]; then
    swaymsg "output * bg '$value' fill" >/dev/null 2>&1
  else
    swaymsg "output * bg $value solid_color" >/dev/null 2>&1
  fi
}

use_fallback() {
  log WARN "falling back: $1"
  if is_valid_image "$LAST_GOOD"; then
    ln -sf "$LAST_GOOD" "$CURRENT"
    if apply_background image "$CURRENT"; then
      log INFO "applied last known-good wallpaper ($LAST_GOOD)"
      notify-send -u normal -i "$ICON_WARNING" "Wallpaper" "Couldn't fetch a new one ($1) -- kept the last good wallpaper"
    fi
  else
    log WARN "no last known-good wallpaper on disk yet either -- using a solid color"
    if apply_background color "$FALLBACK_COLOR"; then
      log INFO "applied solid-color fallback (#$FALLBACK_COLOR)"
      notify-send -u critical -i "$ICON_ERROR" "Wallpaper" "Couldn't fetch a new one ($1), and no previous wallpaper on disk -- using a solid color"
    fi
  fi
}

# --- Network check ---------------------------------------------------------
# Cheap pre-check to skip a doomed download outright; the real download's own
# timeouts below are the authoritative check regardless of what this says.
if command -v nmcli >/dev/null 2>&1; then
  connectivity=$(nmcli networking connectivity check 2>/dev/null || echo unknown)
  log INFO "network connectivity: $connectivity"
  if [ "$connectivity" = "none" ]; then
    use_fallback "no network connectivity"
    exit 0
  fi
fi

# --- Download, with retries and real validation -----------------------------
TMP_FILE=$(mktemp "$ACTIVE_DIR/.download.XXXXXX")
downloaded=false
chosen_idx=""
chosen_mkt=""

for attempt in $(seq 1 "$MAX_RETRIES"); do
  # Re-rolled every attempt, not just once up front -- a retry after a
  # validation failure gets a genuinely fresh index+market to try instead
  # of hammering the same (possibly bad) combination three times.
  chosen_idx=$((RANDOM % (WALLPAPER_MAX_INDEX + 1)))
  chosen_mkt="${WALLPAPER_MARKETS[$((RANDOM % ${#WALLPAPER_MARKETS[@]}))]}"
  url=$(wallpaper_url "$chosen_idx" "$chosen_mkt")
  log INFO "download attempt $attempt/$MAX_RETRIES (index=$chosen_idx, mkt=$chosen_mkt)"
  if curl -fsSL --connect-timeout 10 --max-time 20 -o "$TMP_FILE" "$url"; then
    if is_valid_image "$TMP_FILE"; then
      downloaded=true
      break
    fi
    log WARN "attempt $attempt: response wasn't an image (got $(file -b --mime-type "$TMP_FILE" 2>/dev/null || echo unknown)) -- API is up but returned something unusable, discarding"
  else
    log WARN "attempt $attempt: download failed (curl exit $?)"
  fi
  [ "$attempt" -lt "$MAX_RETRIES" ] && sleep "$RETRY_DELAY"
done

# Filename reflects what was actually fetched (day index + market) rather
# than just today's date -- clicking twice in one day now legitimately
# produces two different files instead of the second overwriting the
# first in Active/ before archiving even sees it.
FILEPATH="$ACTIVE_DIR/wallpaper-$(date +%Y%m%d)-idx${chosen_idx}-${chosen_mkt}.jpg"

if [ "$downloaded" != true ]; then
  rm -f "$TMP_FILE"
  use_fallback "no valid image after $MAX_RETRIES attempts"
  exit 0
fi

# --- Success: archive the old one, promote the new one ---------------------
log INFO "download OK: $(file -b --mime-type "$TMP_FILE"), $(stat -c%s "$TMP_FILE") bytes"

find "$ACTIVE_DIR" -maxdepth 1 -type f ! -name "$(basename "$TMP_FILE")" -exec mv -t "$ARCHIVE_DIR" {} + 2>/dev/null

mv -f "$TMP_FILE" "$FILEPATH"
chmod 644 "$FILEPATH"
cp -f "$FILEPATH" "$LAST_GOOD"
ln -sf "$FILEPATH" "$CURRENT"

archive_count=$(find "$ARCHIVE_DIR" -maxdepth 1 -type f -name '*.jpg' | wc -l)
if [ "$archive_count" -gt "$MAX_ARCHIVE_FILES" ]; then
  prune_count=$((archive_count - MAX_ARCHIVE_FILES))
  find "$ARCHIVE_DIR" -maxdepth 1 -type f -name '*.jpg' -printf '%T@ %p\n' \
    | sort -n | head -n "$prune_count" | cut -d' ' -f2- \
    | xargs -r rm -f
  log INFO "pruned $prune_count old archived wallpaper(s), keeping newest $MAX_ARCHIVE_FILES"
fi

if apply_background image "$CURRENT"; then
  log INFO "applied new wallpaper: $FILEPATH"
  notify-send -u low -i "$CURRENT" "Wallpaper" "New wallpaper applied"
else
  log WARN "couldn't reach sway IPC to apply immediately; current.jpg is updated and will show on next sway start/reload"
  notify-send -u normal -i "$ICON_WARNING" "Wallpaper" "Fetched a new one, but couldn't apply it live -- will show on next sway reload"
fi
