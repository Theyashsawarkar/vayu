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
#
# Random picks still repeated a lot, though: an md5sum of Archive/ showed
# one photo saved 12 times and a dozen more saved 2-3 times, because
# markets share photos and an index points at a different day every day.
# So every applied wallpaper is now recorded in $SEEN_FILE (Bing's own
# image ID, e.g. "GrizzlySwim" out of OHR.GrizzlySwim_EN-US5133524829 --
# the same across every market, unlike the bytes -- plus the file's md5),
# and a run only applies an image whose ID and md5 aren't in it.
# Every index+market pair is looked up in the API's JSON mode, all in
# one parallel curl (no image downloads), then walked shuffled, recent
# days before older ones; only the chosen image is downloaded. The history is
# never pruned with the archive, so "seen" means seen ever, not just
# within the last $MAX_ARCHIVE_FILES. If every candidate has been seen,
# the current wallpaper simply stays -- a repeat is never applied.

set -uo pipefail
# Deliberately not `-e`: this script must always be able to reach its own
# fallback logic, never die partway through on an unexpected error.

BASE_DIR="$HOME/Pictures/Wallpapers"
ACTIVE_DIR="$BASE_DIR/Active"
ARCHIVE_DIR="$BASE_DIR/Archive"
CURRENT="$BASE_DIR/current.jpg"
LAST_GOOD="$BASE_DIR/.last_good.jpg"
SEEN_FILE="$BASE_DIR/.seen"  # TSV: bing-id, md5, date applied, filename
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
# 0-3 = today through 3 days ago -- tried first, so a new wallpaper stays
# "recent" when it can. 4-7 (Bing's API goes no further back) are only
# reached once every recent market+day combination has been seen.
WALLPAPER_RECENT_MAX_INDEX=3
WALLPAPER_MAX_INDEX=7
MAX_RETRIES=3    # lookup rounds / image download failures before giving up
RETRY_DELAY=5

wallpaper_info_url() {
  local idx="$1" mkt="$2"
  printf 'https://bing.biturl.top/?resolution=1920&format=json&index=%s&mkt=%s' "$idx" "$mkt"
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

# --- History of applied wallpapers -------------------------------------------
# First run with this history: seed it with the md5 of everything already
# on disk (no Bing ID known for those, hence "-"), so the archive that
# predates it counts as seen too. A plain TSV read into two hash tables
# once per run: it grows by a line a day, so a database would buy nothing.
if [ ! -f "$SEEN_FILE" ]; then
  find "$ACTIVE_DIR" "$ARCHIVE_DIR" -maxdepth 1 -type f -name '*.jpg' -print0 \
    | xargs -0 -r md5sum \
    | awk -v d="$(date +%Y%m%d)" '!seen[$1]++ { n = $2; sub(/.*\//, "", n); printf "-\t%s\t%s\t%s\n", $1, d, n }' \
    > "$SEEN_FILE"
  log INFO "seeded $SEEN_FILE with $(wc -l < "$SEEN_FILE") existing wallpaper(s)"
fi

declare -A SEEN_IDS=() SEEN_MD5S=()
while IFS=$'\t' read -r s_id s_md5 _; do
  [ -n "$s_id" ] && [ "$s_id" != "-" ] && SEEN_IDS[$s_id]=1
  [ -n "$s_md5" ] && SEEN_MD5S[$s_md5]=1
done < "$SEEN_FILE"

remember() {  # $1 = id, $2 = md5, $3 = filename
  printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$(date +%Y%m%d)" "$3" >> "$SEEN_FILE"
  SEEN_IDS[$1]=1; SEEN_MD5S[$2]=1
}

# --- Look up every index+market at once ---------------------------------------
# One lookup takes ~1.5s, so walking candidates one by one until an
# unseen one turns up could take a minute and a half once most are seen.
# A single parallel curl fetches all of them (8 days x 20 markets) in
# about the time of one -- measured 1.4s for all 160.
LOOKUP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/fetch_wallpaper.XXXXXX")
TMP_FILE=""
trap 'rm -rf "$LOOKUP_DIR"; [ -n "$TMP_FILE" ] && rm -f "$TMP_FILE"' EXIT

# Shuffled, recent days (0..RECENT_MAX) first, older ones after.
candidates() {
  local lo="$1" hi="$2" i m
  for i in $(seq "$lo" "$hi"); do
    for m in "${WALLPAPER_MARKETS[@]}"; do echo "$i $m"; done
  done | shuf
}
mapfile -t CANDIDATES < <(
  candidates 0 "$WALLPAPER_RECENT_MAX_INDEX"
  candidates $((WALLPAPER_RECENT_MAX_INDEX + 1)) "$WALLPAPER_MAX_INDEX"
)

curl_args=()
for cand in "${CANDIDATES[@]}"; do
  read -r idx mkt <<<"$cand"
  curl_args+=(-o "$LOOKUP_DIR/$idx-$mkt.json" "$(wallpaper_info_url "$idx" "$mkt")")
done

answered=0
for attempt in $(seq 1 "$MAX_RETRIES"); do
  # -f: a failed lookup leaves no file; the rest still land.
  curl -fsS -Z --parallel-max 50 --connect-timeout 10 --max-time 30 "${curl_args[@]}" 2>/dev/null
  answered=$(find "$LOOKUP_DIR" -name '*.json' -size +0 | wc -l)
  [ "$answered" -gt 0 ] && break
  log WARN "lookup attempt $attempt/$MAX_RETRIES: no answers"
  [ "$attempt" -lt "$MAX_RETRIES" ] && sleep "$RETRY_DELAY"
done
if [ "$answered" -eq 0 ]; then
  use_fallback "network errors"
  exit 0
fi

# Unseen images, in candidate order, one entry per photo: markets share
# photos, and Bing's ID is the same across them.
picks=()
declare -A listed=()
for cand in "${CANDIDATES[@]}"; do
  read -r idx mkt <<<"$cand"
  img_url=$(jq -r '.url // empty' "$LOOKUP_DIR/$idx-$mkt.json" 2>/dev/null)
  [ -n "$img_url" ] || continue
  # .../th?id=OHR.GrizzlySwim_EN-US5133524829_1920x1080.jpg -> GrizzlySwim;
  # if Bing ever changes that format, the whole id= value still works as
  # an ID (just per-market rather than shared).
  img_id=$(sed -n 's/.*[?&]id=OHR\.\([^_&]*\)_.*/\1/p' <<<"$img_url")
  [ -n "$img_id" ] || img_id=$(sed -n 's/.*[?&]id=\([^&]*\).*/\1/p' <<<"$img_url")
  [ -n "$img_id" ] || img_id="$img_url"
  [ -n "${listed[$img_id]:-}" ] && continue
  listed[$img_id]=1
  [ -n "${SEEN_IDS[$img_id]:-}" ] && continue
  picks+=("$img_id $idx $mkt $img_url")
done
log INFO "$answered/${#CANDIDATES[@]} lookups answered: ${#listed[@]} distinct image(s), ${#picks[@]} not used before"

# --- Download the first unseen one that really is new ------------------------
TMP_FILE=$(mktemp "$ACTIVE_DIR/.download.XXXXXX")
downloaded=false
net_failures=0
for pick in "${picks[@]}"; do
  read -r img_id idx mkt img_url <<<"$pick"
  log INFO "downloading $img_id (index=$idx, mkt=$mkt)"
  if ! curl -fsSL --connect-timeout 10 --max-time 30 -o "$TMP_FILE" "$img_url"; then
    net_failures=$((net_failures + 1))
    log WARN "download of $img_id failed, $net_failures/$MAX_RETRIES"
    [ "$net_failures" -ge "$MAX_RETRIES" ] && break
    sleep "$RETRY_DELAY"
    continue
  fi
  if ! is_valid_image "$TMP_FILE"; then
    log WARN "$img_id: response wasn't an image (got $(file -b --mime-type "$TMP_FILE" 2>/dev/null || echo unknown)), discarding"
    continue
  fi
  img_md5=$(md5sum "$TMP_FILE" | cut -d' ' -f1)
  if [ -n "${SEEN_MD5S[$img_md5]:-}" ]; then
    # Same bytes as a wallpaper from before the history had IDs. Record
    # the ID too, so next time it's skipped without downloading.
    log INFO "skip $img_id: identical to an earlier wallpaper (md5 $img_md5)"
    remember "$img_id" "$img_md5" "-"
    continue
  fi
  downloaded=true
  break
done

if [ "$downloaded" != true ]; then
  if [ "$net_failures" -ge "$MAX_RETRIES" ]; then
    use_fallback "network errors"
  else
    # Not an error: Bing just hasn't published anything not already used.
    # Leave the current wallpaper alone rather than repeat an old one.
    log INFO "no unseen wallpaper available -- keeping the current one"
    notify-send -u low -i "$ICON_WALLPAPER" "Wallpaper" "No new wallpaper available yet -- keeping the current one"
  fi
  exit 0
fi

# Named after Bing's image ID, so the archive says which photo it is.
FILEPATH="$ACTIVE_DIR/wallpaper-$(date +%Y%m%d)-${img_id//[^A-Za-z0-9_-]/_}.jpg"

# --- Success: archive the old one, promote the new one ---------------------
log INFO "download OK: $(file -b --mime-type "$TMP_FILE"), $(stat -c%s "$TMP_FILE") bytes"

find "$ACTIVE_DIR" -maxdepth 1 -type f ! -name "$(basename "$TMP_FILE")" -exec mv -t "$ARCHIVE_DIR" {} + 2>/dev/null

mv -f "$TMP_FILE" "$FILEPATH"
chmod 644 "$FILEPATH"
cp -f "$FILEPATH" "$LAST_GOOD"
ln -sf "$FILEPATH" "$CURRENT"
remember "$img_id" "$img_md5" "$(basename "$FILEPATH")"

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
