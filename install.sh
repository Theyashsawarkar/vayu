#!/usr/bin/env bash
# Bootstraps this entire Arch + Sway desktop from a bare Arch install.
#
# Run from a TTY right after `archinstall` + first boot + login as your
# normal (sudo-capable) user, with networking already up:
#
#   bash <(curl -fsSL https://raw.githubusercontent.com/Theyashsawarkar/vayu/main/install.sh)
#
# Prompts once for an update channel (Stable/Nightly, Stable default) unless
# one is passed directly as the first argument -- `stable` or `nightly`,
# case-insensitive -- which skips the prompt entirely:
#
#   bash <(curl -fsSL .../main/install.sh) stable
#   bash <(curl -fsSL .../main/install.sh) nightly
#
# This is what the docs site's own two download buttons hand you. The copy
# fetched by curl only bootstraps: once the repo is cloned it re-runs the
# install.sh from the checked-out branch, so a Nightly install runs
# Nightly's installer against Nightly's package lists, never main's
# installer against a branch it doesn't know. Anything else passed as the
# argument is a hard error, not a silent fallback to Stable.
#
# Idempotent: safe to re-run (e.g. after adding a package to packages/*.txt,
# or to repair a machine `vayu-verify` reports as drifted).
#
# Logging: everything (the full output, plus a command trace) goes to
# ~/.local/state/vayu/install-logs/install-<date>.log, with latest.log
# pointing at the newest. Each step is timed and reported; a failing
# non-critical step (one AUR package, Homebrew...) is recorded and the
# rest still runs, and the summary at the end lists exactly what failed.
# Only steps everything else depends on (prerequisites, the repo,
# official packages, stow) stop the run.
#
# What it sets up lives in the repo, not here: packages/pacman.txt and
# aur.txt (packages), packages/manifest.sh (services, masks, groups,
# user-level tools), system/ (root-owned files under /), greeter/ (login
# screen), splash/ (boot splash), ai/ (AI tools: vayu-elevate), and every other
# top-level directory (stowed into ~).

set -Eeuo pipefail

DOTFILES_DIR="$HOME/dotfiles"
REPO_URL="https://github.com/Theyashsawarkar/vayu.git"
BACKUP_DIR="$HOME/.dotfiles-backup"
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/vayu/install-logs"
# Set by login, but not by every way of starting a shell (su -c, docker exec,
# systemd-run): with set -u an unset USER ended the run in preflight.
USER=${USER:-$(id -un)}
export USER

# --- Logging ------------------------------------------------------------------
# A re-exec (see "Hand over to the repo's installer" below) inherits the
# already-tee'd stdout and the log path, so it must not tee again.
if [ -z "${VAYU_INSTALL_LOG:-}" ]; then
  mkdir -p "$LOG_DIR"
  VAYU_INSTALL_LOG="$LOG_DIR/install-$(date +%Y%m%d-%H%M%S).log"
  ln -sfn "$(basename "$VAYU_INSTALL_LOG")" "$LOG_DIR/latest.log"
  export VAYU_INSTALL_LOG
  # Terminal gets the output as-is; the log gets it without colour codes
  # and without progress-bar redraws (keeps the text after the last \r).
  exec > >(tee >(sed -u -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/.*\r//' >> "$VAYU_INSTALL_LOG")) 2>&1
fi
LOG_FILE=$VAYU_INSTALL_LOG
# Command trace into the log only (not the terminal): every command with
# its line number, so a failure can be traced to exactly what ran.
exec {TRACE_FD}>>"$LOG_FILE"
BASH_XTRACEFD=$TRACE_FD
PS4='+ [${BASH_SOURCE[0]##*/}:${LINENO}] '
set -x

# Carried across the hand-over to the repo's installer (see Main), so the
# summary covers the whole run.
RUN_START=${VAYU_RUN_START:-$EPOCHSECONDS}
# What this run is executing, to notice when sync_repo pulls a newer
# install.sh (bash keeps reading the old file, so it would carry on with
# the old code). Empty for the curl bootstrap copy, a pipe.
SELF_SUM=""
[ -f "${BASH_SOURCE[0]}" ] && SELF_SUM=$(sha256sum < "${BASH_SOURCE[0]}")
FAILURES_FILE=${VAYU_FAILURES_FILE:-$(mktemp "${TMPDIR:-/tmp}/vayu-install-failures.XXXXXX")}
STEP_RESULTS=()
[ -n "${VAYU_STEP_RESULTS:-}" ] && mapfile -t STEP_RESULTS <<<"$VAYU_STEP_RESULTS"
FAILED_STEPS=${VAYU_FAILED_STEPS:-0}
SCRIPT_ARGS="$*"

ts() { date +%H:%M:%S; }
log()  { { set +x; } 2>/dev/null; printf '\n\033[1;34m==>\033[0m [%s] %s\n' "$(ts)" "$1"; set -x; }
info() { { set +x; } 2>/dev/null; printf '    %s\n' "$1"; set -x; }
warn() { { set +x; } 2>/dev/null; printf '\033[1;33m  ! %s\033[0m\n' "$1"; set -x; }
err()  { { set +x; } 2>/dev/null; printf '\033[1;31m  x %s\033[0m\n' "$1"; set -x; }
# Something specific that failed inside a step (a package, a unit):
# listed again in the final summary.
note_failure() { echo "$1" >> "$FAILURES_FILE"; err "$1"; }

on_err() {  # ERR trap: the exact command that failed, and where
  local rc=$1 line=$2 cmd=$3
  { set +x; } 2>/dev/null
  case "$cmd" in
    # A step function handing back its own status (return "$bad", or a
    # final [ test ]): the items that failed were already listed above.
    return*|\[*) printf '\033[1;31m  x step reported failure (exit %s); the x lines above say what failed\033[0m\n' "$rc" ;;
    *) printf '\033[1;31m  x command failed (exit %s) at %s line %s: %s\033[0m\n' "$rc" "${BASH_SOURCE[1]##*/}" "$line" "$cmd" ;;
  esac
  set -x
}
trap 'on_err $? $LINENO "$BASH_COMMAND"' ERR

summary() {
  local rc=$?
  { set +x; } 2>/dev/null
  # errexit off: a failing diagnostic (df on a missing /boot...) must not
  # end the summary before it prints.
  set +e +o pipefail
  trap - ERR
  [ -n "${SUDO_KEEPALIVE_PID:-}" ] && kill "$SUDO_KEEPALIVE_PID" 2>/dev/null
  local took=$((EPOCHSECONDS - RUN_START))
  printf '\n\033[1m==> Summary (%dm%02ds)\033[0m\n' $((took / 60)) $((took % 60))
  local r
  for r in "${STEP_RESULTS[@]}"; do printf '    %s\n' "$r"; done
  if [ -s "$FAILURES_FILE" ]; then
    printf '\n    Failed items:\n'
    sed 's/^/      - /' "$FAILURES_FILE"
  fi
  rm -f "$FAILURES_FILE"
  if [ "$rc" -ne 0 ] || [ "$FAILED_STEPS" -gt 0 ]; then
    diagnostics
  fi
  if [ "$rc" -eq 0 ] && [ "$FAILED_STEPS" -eq 0 ]; then
    printf '\n\033[1;32mDone.\033[0m Reboot and log in at the tuigreet prompt on tty1 (it starts Sway).\n'
    echo "Group changes (docker, input) take effect at that next login."
  else
    printf '\n\033[1;31mFinished with problems.\033[0m Fix what is listed above and re-run: it skips what is already done.\n'
    echo "In the log: search \"command failed\" for each failing command, and the"
    echo "diagnostics section at the end for clock, disk, network and pacman state."
  fi
  echo "Full log: $LOG_FILE"
  [ "$rc" -eq 0 ] && [ "$FAILED_STEPS" -gt 0 ] && rc=1
  exit "$rc"
}

# What to do when a step fails, printed under it in the summary. The log
# has the exact failing command (search it for "command failed").
remedy() {
  case "$1" in
    preflight) echo "fix what the 'x' line above says, then re-run" ;;
    prerequisites)
      echo "usually a mirror, the keyring or the clock. Try, then re-run:"
      echo "  timedatectl set-ntp true          (wrong clock breaks signatures/TLS)"
      echo "  sudo pacman -Sy archlinux-keyring (\"invalid or corrupted package\")"
      echo "  sudo reflector -c <country> -l 10 --sort rate --save /etc/pacman.d/mirrorlist"
      echo "                                    (slow/404 mirrors; pacman -S reflector)" ;;
    sync_repo)
      echo "github.com unreachable, or ~/dotfiles diverged: cd ~/dotfiles && git status"
      echo "to start clean: mv ~/dotfiles ~/dotfiles.old and re-run" ;;
    install_official)
      echo "see Failed items. 'not in the repos': the package was renamed/dropped --"
      echo "fix packages/pacman.txt. 'failed to install': sudo pacman -S <pkg> shows why"
      echo "(file conflict: pacman -Qo <file>; PGP error: sudo pacman -Sy archlinux-keyring)" ;;
    bootstrap_yay)
      echo "needs base-devel + git. By hand: git clone https://aur.archlinux.org/yay-bin.git"
      echo "  && cd yay-bin && makepkg -si, then re-run" ;;
    install_aur)
      echo "AUR builds break upstream now and then. For each failed package:"
      echo "  yay -S <pkg>   (full error)   rm -rf ~/.cache/yay/<pkg>   (stale build dir)"
      echo "  https://aur.archlinux.org/packages/<pkg> (comments usually have the fix)" ;;
    stow_all)
      echo "see what's in the way: stow -n -v -R -d ~/dotfiles -t ~ <package>"
      echo "move that file aside and re-run (earlier conflicts are in ~/.dotfiles-backup/)" ;;
    apply_system_files) echo "~/dotfiles/system/apply.sh --check lists what differs; run it without --check for the error" ;;
    apply_greeter)
      echo "re-run ~/dotfiles/greeter/apply.sh for the error. Login still works: tuigreet-launch"
      echo "falls back to stock tuigreet (or greetd's text login) if tuigreet-ace didn't build" ;;
    apply_splash)
      echo "~/dotfiles/splash/apply.sh --check lists what differs; run it without --check for the error."
      echo "Booting is unaffected until mkinitcpio -P succeeds; a failed run leaves the old text boot" ;;
    apply_ai) echo "~/dotfiles/ai/apply.sh --check lists what differs; run it without --check for the error" ;;
    setup_shell|setup_tmux) echo "a git clone failed (network/GitHub); re-run" ;;
    setup_nvim) echo "open nvim and run :Lazy restore to see which plugin failed" ;;
    setup_node) echo "sudo corepack enable (needs the corepack package)" ;;
    setup_brew) echo "Homebrew's own error is above; after installing it, 'brew doctor' explains most failures" ;;
    setup_claude_hooks) echo "~/dotfiles/scripts/.local/bin/claude-hooks-install.sh shows the error (needs jq)" ;;
    setup_system_services) echo "for each failed unit: systemctl status <unit>; journalctl -b -u <unit>" ;;
    setup_groups) echo "sudo usermod -aG <group> \$USER, then log out and back in" ;;
    setup_user_services)
      echo "needs a real login session (a TTY login, not su/sudo -i/ssh without lingering):"
      echo "  systemctl --user status <unit>; journalctl --user -b -u <unit>" ;;
    apply_theme) echo "dconf needs a D-Bus session: re-run from a TTY login, or let it be -- only GTK theming" ;;
    first_wallpaper) echo "harmless: wallpaper.timer fetches one later, or run ~/.local/bin/fetch_wallpaper.sh" ;;
    verify) echo "each FAIL above names what drifted; a re-run fixes most, vayu-verify -v lists everything" ;;
  esac
}

# On failure: the state that explains most install problems, into the log
# only (the terminal already has the summary).
diagnostics() {
  {
    echo
    echo "==================== diagnostics (failed run) ===================="
    echo "--- date / clock";      date; timedatectl 2>&1 | head -8
    echo "--- disk";              df -h / "$HOME" /boot 2>&1
    echo "--- memory";            free -h
    echo "--- network";           ip -br addr 2>&1; getent hosts archlinux.org github.com 2>&1
    echo "--- pacman lock";       ls -l /var/lib/pacman/db.lck 2>&1
    echo "--- pacman.log (last 40)"; tail -n 40 /var/log/pacman.log 2>&1
    echo "--- journal errors this boot (last 40)"; journalctl -b -p err -n 40 --no-pager 2>&1
    echo "--- failed units";      systemctl --failed --no-legend 2>&1; systemctl --user --failed --no-legend 2>&1
    echo "=================================================================="
  } >> "$LOG_FILE" 2>&1
}

# run_step [--critical] "title" function
# Runs the step in a subshell with errexit on, so its first failing
# command ends that step only. A --critical step's failure ends the run.
run_step() {
  local critical=false
  if [ "$1" = "--critical" ]; then critical=true; shift; fi
  local title=$1 fn=$2 start=$SECONDS rc=0
  log "$title"
  trap - ERR   # the subshell sets its own; don't report its exit twice
  set +e
  (
    trap 'on_err $? $LINENO "$BASH_COMMAND"' ERR
    set -e
    "$fn"
  )
  rc=$?
  set -e
  trap 'on_err $? $LINENO "$BASH_COMMAND"' ERR
  local took=$((SECONDS - start))
  if [ "$rc" -eq 0 ]; then
    STEP_RESULTS+=("ok    $title (${took}s)")
  else
    STEP_RESULTS+=("FAIL  $title (exit $rc, ${took}s)")
    local l first=true
    while IFS= read -r l; do
      if $first; then STEP_RESULTS+=("        fix: $l"); first=false
      else STEP_RESULTS+=("             $l"); fi
    done < <(remedy "$fn")
    FAILED_STEPS=$((FAILED_STEPS + 1))
    err "step failed: $title -- details in $LOG_FILE"
    if $critical; then
      err "everything after this depends on it, stopping here"
      exit 1
    fi
  fi
}

# Package list files: one name per line, blank lines and # comments allowed.
read_list() { { grep -v '^\s*#' "$1" || true; } | awk 'NF { print $1 }'; }

# --- Steps ----------------------------------------------------------------------

preflight() {
  if [ "$(id -u)" -eq 0 ]; then
    err "run this as your normal user, not root (it calls sudo where needed)"
    return 1
  fi
  [ -f /etc/arch-release ] || { err "this installer is for Arch Linux"; return 1; }
  info "user=$USER host=$(cat /etc/hostname 2>/dev/null) kernel=$(uname -r)"
  info "cpu=$(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | xargs || true) ram=$(free -h | awk '/^Mem:/{print $2}')"
  info "free space in \$HOME: $(df -h --output=avail "$HOME" | tail -1 | xargs)"
  info "installer: ${BASH_SOURCE[0]} args: ${SCRIPT_ARGS:-none}"
  local avail_gb
  avail_gb=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc 0-9)
  if [ "$avail_gb" -lt 8 ]; then
    err "only ${avail_gb}G free in \$HOME; a full install needs roughly 15G -- free space or grow the partition"
    return 1
  fi
  [ "$avail_gb" -ge 15 ] || warn "only ${avail_gb}G free; a full install needs roughly 15G"
  # The single password prompt of the run (kept fresh afterwards). A fresh
  # archinstall user may not be allowed sudo yet.
  if ! command -v sudo >/dev/null 2>&1; then
    err "sudo isn't installed. As root: pacman -S sudo, then the wheel step below"
    return 1
  fi
  if ! sudo -v; then
    err "$USER can't use sudo. As root: usermod -aG wheel $USER, then EDITOR=nano visudo"
    err "and uncomment '%wheel ALL=(ALL:ALL) ALL'; log out, log back in, re-run"
    return 1
  fi
  # A wrong clock fails TLS (curl, git) and package signatures with
  # confusing errors; turn on NTP and give it a moment.
  if [ "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)" = "no" ]; then
    warn "clock not NTP-synchronized ($(date)); enabling NTP"
    sudo timedatectl set-ntp true || true
    local i
    for i in $(seq 15); do
      [ "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)" = "yes" ] && break
      sleep 1
    done
    info "clock now: $(date) (synchronized: $(timedatectl show -p NTPSynchronized --value 2>/dev/null || echo unknown))"
  fi
  local host
  for host in https://archlinux.org https://github.com https://aur.archlinux.org; do
    curl -fsS --max-time 15 -o /dev/null "$host" || { err "can't reach $host -- check networking (nmtui) and re-run"; return 1; }
  done
  info "network: archlinux.org, github.com and aur.archlinux.org reachable"
  # A pacman lock with no pacman running is left over from an interrupted
  # run and would fail every install below.
  if [ -e /var/lib/pacman/db.lck ] && ! pgrep -x pacman >/dev/null; then
    warn "removing stale pacman lock /var/lib/pacman/db.lck (no pacman running)"
    sudo rm -f /var/lib/pacman/db.lck
  fi
}

prerequisites() {
  # Keyring first: an install image's keyring is often older than the
  # packages' signatures. Then a full upgrade: Arch doesn't support
  # partial upgrades (-Sy then -S of a few packages can break libraries).
  sudo pacman -Sy --needed --noconfirm archlinux-keyring
  sudo pacman -Su --noconfirm
  sudo pacman -S --needed --noconfirm git stow base-devel curl jq
}

choose_branch() {
  # Update channel: either handed directly as $1 (what the docs site's
  # own download buttons pass), or asked interactively here at first
  # install. See docs/VERSIONING.md's "Update channels": this is the
  # only place the choice is made; update-check.sh just reads whichever
  # branch is checked out.
  if [ "${1:-}" != "" ]; then
    case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
      stable) BRANCH="main" ;;
      nightly) BRANCH="development" ;;
      *)
        echo "Unknown channel '$1' -- expected 'stable' or 'nightly'." >&2
        exit 1
        ;;
    esac
  else
    # /dev/tty, not stdin, so this still asks under `curl ... | bash`.
    # No terminal at all: falls through to Stable, never hangs.
    echo
    echo "Which update channel?"
    echo "  1) Stable  (main -- tagged releases only) [default]"
    echo "  2) Nightly (development -- day-to-day work, may break)"
    CHANNEL_CHOICE=""
    read -r -p "Choice [1]: " CHANNEL_CHOICE </dev/tty || true
    case "$CHANNEL_CHOICE" in
      2) BRANCH="development" ;;
      *) BRANCH="main" ;;
    esac
  fi
}

sync_repo() {
  if [ -d "$DOTFILES_DIR/.git" ]; then
    info "branch: $(git -C "$DOTFILES_DIR" rev-parse --abbrev-ref HEAD)"
    # Pulled even with local changes (nvim rewrites lazy-lock.json on every
    # plugin update, so a clean tree is rare): git refuses on its own if a
    # change would be overwritten, and only then is the pull skipped.
    [ -n "$(git -C "$DOTFILES_DIR" status --porcelain)" ] && info "local changes: $(git -C "$DOTFILES_DIR" status --porcelain | wc -l) file(s); pulling around them"
    if ! git -C "$DOTFILES_DIR" pull --ff-only; then
      warn "git pull --ff-only failed (a local change in the way, or a diverged branch: cd ~/dotfiles && git status); installing from the local checkout as it is"
    fi
  elif [ -e "$DOTFILES_DIR" ]; then
    err "$DOTFILES_DIR exists but isn't a git checkout; move it away and re-run"
    return 1
  else
    git clone -b "$BRANCH" "$REPO_URL" "$DOTFILES_DIR"
  fi
  info "at $(git -C "$DOTFILES_DIR" log -1 --format='%h %s (%cs)')"
}

# --needed skips a package that's already there as a dependency of another
# one, so it stays "installed as a dependency" and the next orphan cleanup
# (pacman -Rns $(pacman -Qdtq)) removes it -- mpv was one. Mark every listed
# package that's installed as explicit. Groups (pacman -Sg) aren't packages.
mark_explicit() {
  local p deps=()
  for p in "$@"; do
    if pacman -Qdq "$p" >/dev/null 2>&1; then deps+=("$p"); fi
  done
  [ "${#deps[@]}" -eq 0 ] && return 0
  info "marking as explicitly installed: ${deps[*]}"
  sudo pacman -D --asexplicit "${deps[@]}" >/dev/null
}

install_official() {
  cd "$DOTFILES_DIR"
  local want=() avail=() failed=() p
  mapfile -t want < <(read_list packages/pacman.txt)
  # Check names first: one that left the repos (renamed, dropped) would
  # otherwise fail the whole batch with a one-line error.
  for p in "${want[@]}"; do
    if pacman -Si "$p" >/dev/null 2>&1 || pacman -Sg "$p" >/dev/null 2>&1; then
      avail+=("$p")
    else
      note_failure "pacman: '$p' (packages/pacman.txt) is not in the repos"
    fi
  done
  info "${#avail[@]}/${#want[@]} packages available, installing (already installed ones are skipped)"
  if ! sudo pacman -S --needed --noconfirm "${avail[@]}"; then
    warn "batch install failed; retrying one package at a time to find the culprit"
    for p in "${avail[@]}"; do
      sudo pacman -S --needed --noconfirm "$p" || { failed+=("$p"); note_failure "pacman: '$p' failed to install (sudo pacman -S $p shows why)"; }
    done
  fi
  mark_explicit "${avail[@]}"
  [ "${#avail[@]}" -eq "${#want[@]}" ] && [ "${#failed[@]}" -eq 0 ]
}

bootstrap_yay() {
  if command -v yay >/dev/null 2>&1; then info "yay already installed"; return 0; fi
  local tmp
  tmp=$(mktemp -d)
  git clone --depth=1 https://aur.archlinux.org/yay.git "$tmp/yay"
  if ! (cd "$tmp/yay" && makepkg -si --noconfirm --needed); then
    # yay builds from source with Go; yay-bin is the same program prebuilt.
    warn "building yay failed; trying the prebuilt yay-bin"
    git clone --depth=1 https://aur.archlinux.org/yay-bin.git "$tmp/yay-bin"
    (cd "$tmp/yay-bin" && makepkg -si --noconfirm --needed)
  fi
  rm -rf "$tmp"
}

# An AUR package with packages/aur-patches/<pkg>.sed gets that sed run on
# its PKGBUILD before building, for when upstream's PKGBUILD is broken (a
# dependency renamed, say) and the fix is known. Built with makepkg, then
# installed with pacman --ask=4, which says yes to replacing a conflicting
# package (stock sway, from the fallback below, when swayfx builds again).
build_patched_aur() {
  local p=$1 patch="$DOTFILES_DIR/packages/aur-patches/$1.sed" tmp aurver
  aurver=$(curl -fsS --max-time 30 "https://aur.archlinux.org/rpc/v5/info?arg[]=$p" | jq -r '.results[0].Version // empty') || aurver=""
  if [ -n "$aurver" ] && [ "$(pacman -Q "$p" 2>/dev/null | cut -d' ' -f2)" = "$aurver" ]; then
    info "$p $aurver already installed (patched build)"
    return 0
  fi
  tmp=$(mktemp -d)
  git clone --depth=1 "https://aur.archlinux.org/$p.git" "$tmp/$p"
  sed -i -f "$patch" "$tmp/$p/PKGBUILD"
  info "patched $p's PKGBUILD with packages/aur-patches/$p.sed:"
  git -C "$tmp/$p" --no-pager diff --stat
  (cd "$tmp/$p" && makepkg -s --noconfirm --needed) || { rm -rf "$tmp"; return 1; }
  # shellcheck disable=SC2046
  sudo pacman -U --noconfirm --ask=4 $(find "$tmp/$p" -maxdepth 1 -name "*.pkg.tar.*" ! -name "*-debug-*" ! -name "*.sig")
  rm -rf "$tmp"
}

install_aur() {
  cd "$DOTFILES_DIR"
  local want=() avail=() failed=() found p q=""
  mapfile -t want < <(read_list packages/aur.txt)
  for p in "${want[@]}"; do q+="&arg[]=$p"; done
  # One AUR RPC call for every name; if the RPC itself is down, skip the
  # check and let yay report.
  if found=$(curl -fsS --max-time 30 "https://aur.archlinux.org/rpc/v5/info?${q#&}" | jq -r '.results[].Name'); then
    for p in "${want[@]}"; do
      if grep -qx "$p" <<<"$found" || pacman -Si "$p" >/dev/null 2>&1; then avail+=("$p")
      else note_failure "aur: '$p' (packages/aur.txt) is not in the AUR"; fi
    done
  else
    warn "AUR RPC unreachable, skipping the name check"
    avail=("${want[@]}")
  fi
  # cleanAfter: drop each build dir's sources and built packages once
  # installed. Without it ~/.cache/yay kept every version ever built (14G).
  yay -Y --save --cleanafter
  local yay_opts=(--needed --noconfirm --answerdiff None --answerclean None --removemake)
  # Patched packages first, and kept out of yay's batch (it would build the
  # broken PKGBUILD).
  local plain=()
  for p in "${avail[@]}"; do
    if [ -f "packages/aur-patches/$p.sed" ]; then
      build_patched_aur "$p" || { failed+=("$p"); note_failure "aur: '$p' failed to build even with packages/aur-patches/$p.sed (see https://aur.archlinux.org/packages/$p comments)"; }
    else
      plain+=("$p")
    fi
  done
  info "${#plain[@]} more to build/install with yay"
  if [ "${#plain[@]}" -gt 0 ] && ! yay -S "${yay_opts[@]}" "${plain[@]}"; then
    warn "batch install failed; retrying one package at a time to find the culprit"
    for p in "${plain[@]}"; do
      yay -S "${yay_opts[@]}" "$p" || { failed+=("$p"); note_failure "aur: '$p' failed to build/install (retry: yay -S $p; see https://aur.archlinux.org/packages/$p)"; }
    done
  fi
  # swayfx is the compositor: without it the login screen has no session
  # to start. Stock sway reads the same config (swayfx-only lines like
  # blur/corner_radius just get flagged) and keeps the machine usable.
  if ! command -v sway >/dev/null 2>&1; then
    note_failure "no sway after the AUR step (swayfx failed); installed stock sway as a fallback -- re-run install.sh later to swap swayfx back in"
    sudo pacman -S --needed --noconfirm sway || note_failure "pacman: fallback 'sway' failed to install too"
  fi
  mark_explicit "${avail[@]}"
  [ "${#avail[@]}" -eq "${#want[@]}" ] && [ "${#failed[@]}" -eq 0 ]
}

stow_all() {
  cd "$DOTFILES_DIR"
  local pkgs=() out targets f backup n=0
  # Every top-level dir except the non-stow ones: one list, shared with
  # update-apply.sh and vayu-verify.
  mapfile -t pkgs < <(./scripts/.local/bin/dotfiles-stow-packages "$DOTFILES_DIR")
  [ "${#pkgs[@]}" -gt 0 ] || { err "dotfiles-stow-packages listed nothing"; return 1; }
  info "packages: ${pkgs[*]}"
  # Real directories first (STOW_REAL_DIRS, manifest.sh), so stow links
  # files inside them instead of folding the whole directory into the
  # repo. A machine set up before this has folded links there: replace each
  # with a real directory, moving any app data that landed in the repo
  # through it back to ~ (the restow below links the tracked files again).
  local d t target f moved
  for d in "${STOW_REAL_DIRS[@]}"; do
    t="$HOME/$d"
    if [ -L "$t" ] && target=$(readlink -f "$t") && [[ "$target" == "$DOTFILES_DIR"/* ]]; then
      rm "$t"
      mkdir -p "$t"
      moved=0
      while IFS= read -r f; do
        [ -n "$f" ] || continue
        mkdir -p "$t/$(dirname "$f")"
        mv "$target/$f" "$t/$f"
        moved=$((moved + 1))
      done < <(git -C "$target" ls-files --others -- . 2>/dev/null)
      warn "~/$d was a link into the repo; now a real directory ($moved untracked file(s) moved back out of ${target#"$DOTFILES_DIR"/})"
    elif [ ! -e "$t" ]; then
      mkdir -p "$t"
    fi
  done
  # Dry run first to find what's in the way. stow 2.4 reports a real file
  # as "... over existing target X since ..." and a symlink it doesn't own
  # as "existing target is not owned by stow: X"; both get moved aside
  # (into a per-run folder, so re-runs never overwrite older backups).
  out=$(stow -n -v -R -d "$DOTFILES_DIR" -t "$HOME" "${pkgs[@]}" 2>&1 || true)
  # (|| true: no conflicts means grep matches nothing, which pipefail
  # would otherwise turn into a failed step.)
  targets=$( { grep -oE 'over existing target [^ ]+' <<<"$out" | awk '{print $4}' || true
               grep -oE 'existing target is not owned by stow: .+' <<<"$out" | sed 's/.*: //' || true; } | sort -u)
  backup="$BACKUP_DIR/$(date +%Y%m%d-%H%M%S)"
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ -e "$HOME/$f" ] || [ -L "$HOME/$f" ]; then
      mkdir -p "$backup/$(dirname "$f")"
      mv "$HOME/$f" "$backup/$f"
      info "backed up ~/$f -> $backup/$f"
      n=$((n + 1))
    fi
  done <<<"$targets"
  [ "$n" -gt 0 ] && info "$n conflicting file(s) moved to $backup"
  # -R (restow) also drops links to files that were removed from the repo.
  stow -R -v -d "$DOTFILES_DIR" -t "$HOME" "${pkgs[@]}"
}

apply_system_files() { "$DOTFILES_DIR/system/apply.sh"; }

apply_greeter() {
  sudo mkdir -p /etc/greetd
  "$DOTFILES_DIR/greeter/apply.sh"
}

apply_splash() { "$DOTFILES_DIR/splash/apply.sh"; }

apply_ai() { "$DOTFILES_DIR/ai/apply.sh"; }

clone_if_missing() {  # url dest: also replaces a clone an interrupted run left broken
  if [ -d "$2" ] && git -C "$2" rev-parse --verify -q HEAD >/dev/null 2>&1; then
    info "already present: $2"
    return 0
  fi
  rm -rf "$2"
  git clone --depth=1 "$1" "$2"
}

setup_shell() {
  # The path /etc/shells lists (pam_shells and some login paths refuse any
  # other). Not `command -v zsh`: with /usr/sbin ahead of /usr/bin in PATH
  # (a symlink on Arch) that gives /usr/sbin/zsh, which isn't listed.
  local zsh
  if grep -qx /usr/bin/zsh /etc/shells; then zsh=/usr/bin/zsh
  else zsh=$(grep -m1 -xE '/(usr/)?bin/zsh' /etc/shells || command -v zsh); fi
  if [ "$(getent passwd "$USER" | cut -d: -f7)" != "$zsh" ]; then
    sudo chsh -s "$zsh" "$USER"
  fi
  if [ ! -d "$HOME/.oh-my-zsh" ]; then
    # Downloaded to a file first: `sh -c "$(curl ...)"` runs an empty
    # script, and "succeeds", when the download fails.
    local omz
    omz=$(mktemp)
    curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh -o "$omz"
    # ZSH pinned: an exported ZSH from a running zsh would redirect it.
    ZSH="$HOME/.oh-my-zsh" RUNZSH=no CHSH=no KEEP_ZSHRC=yes sh "$omz"
    rm -f "$omz"
  fi
  local c
  for c in "${ZSH_CLONES[@]}"; do
    clone_if_missing "${c%% *}" "$HOME/.oh-my-zsh/custom/${c#* }"
  done
}

setup_tmux() {
  # Every `set -g @plugin 'owner/repo'` in tmux.conf (tpm included),
  # cloned where TPM keeps them. Not TPM's own install_plugins: it asks a
  # running tmux server for its path, and with no server yet that can come
  # back empty ("/").
  local spec
  while read -r spec; do
    clone_if_missing "https://github.com/$spec" "$HOME/.tmux/plugins/${spec##*/}"
  done < <(sed -nE "s/^set -g @plugin '([^']+)'.*/\1/p" "$DOTFILES_DIR/tmux/.config/tmux/tmux.conf")
}

setup_nvim() {
  # lazy.nvim bootstraps itself and installs the plugins pinned in
  # lazy-lock.json; otherwise this happens on the first `nvim`.
  timeout 900 nvim --headless "+Lazy! restore" +qa
}

setup_node() {
  # /usr/bin/pnpm, pnpx and yarn are corepack shims, not packages.
  sudo corepack enable
}

setup_brew() {
  local brew=/home/linuxbrew/.linuxbrew/bin/brew
  if [ ! -x "$brew" ]; then
    local inst
    inst=$(mktemp)
    curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$inst"
    NONINTERACTIVE=1 /bin/bash "$inst"
    rm -f "$inst"
  fi
  eval "$("$brew" shellenv bash)"
  brew install "${BREW_FORMULAE[@]}"
}

setup_claude_hooks() {
  # ~/.claude/CLAUDE.md comes from the stowed claude/ package; settings.json
  # is merged into rather than stowed (see the script for why).
  "$DOTFILES_DIR/scripts/.local/bin/claude-hooks-install.sh"
}

setup_system_services() {
  local u bad=0
  for u in "${SYSTEM_UNITS_NOW[@]}"; do
    sudo systemctl enable --now "$u" || { note_failure "systemctl enable --now $u (systemctl status $u)"; bad=1; }
  done
  # Enabled, not started: greetd would take over this TTY mid-script; it
  # starts on the reboot the summary asks for.
  for u in "${SYSTEM_UNITS_ENABLE[@]}"; do
    sudo systemctl enable "$u" || { note_failure "systemctl enable $u"; bad=1; }
  done
  for u in "${SYSTEM_UNITS_DISABLED[@]}"; do
    if systemctl cat "$u" >/dev/null 2>&1; then
      sudo systemctl disable "$u" || { note_failure "systemctl disable $u"; bad=1; }
    fi
  done
  sudo systemctl mask "${SYSTEM_UNITS_MASKED[@]}" || { note_failure "systemctl mask"; bad=1; }
  # ufw.service only loads the rules; `ufw enable` is what turns the
  # firewall on (default: deny incoming, allow outgoing).
  for u in "${UFW_ALLOW[@]}"; do
    sudo ufw allow "$u" || { note_failure "ufw allow $u"; bad=1; }
  done
  sudo ufw --force enable || { note_failure "ufw enable"; bad=1; }
  return "$bad"
}

setup_groups() {
  local g
  for g in "${USER_GROUPS[@]}"; do
    sudo usermod -aG "$g" "$USER"
  done
}

setup_user_services() {
  local u bad=0
  systemctl --user daemon-reload
  for u in "${USER_UNITS_NOW[@]}"; do
    systemctl --user enable --now "$u" || { note_failure "systemctl --user enable --now $u"; bad=1; }
  done
  for u in "${USER_UNITS_ENABLE[@]}"; do
    systemctl --user enable "$u" || { note_failure "systemctl --user enable $u"; bad=1; }
  done
  return "$bad"
}

apply_theme() {
  # gtk/'s settings.ini sets the theme name, but GNOME-aware apps read the
  # active theme from dconf, so both are needed.
  local s
  for s in "${DCONF_SETTINGS[@]}"; do
    dconf write "${s%% *}" "${s#* }"
  done
}

first_wallpaper() {
  # The timer's first run is at midnight; sway and swaylock both read
  # current.jpg, so fetch one now. (No sway yet: it just saves the file.)
  [ -s "$HOME/Pictures/Wallpapers/current.jpg" ] && { info "already have a wallpaper"; return 0; }
  # Judged by the file, not the exit code: with no sway running yet the
  # script can't apply it live, which is expected here.
  timeout 180 "$HOME/.local/bin/fetch_wallpaper.sh" || warn "fetch_wallpaper.sh exited $?; checking whether it saved one anyway"
  [ -s "$HOME/Pictures/Wallpapers/current.jpg" ]
}

verify() { "$DOTFILES_DIR/scripts/.local/bin/vayu-verify"; }

# --- Main -------------------------------------------------------------------------
trap summary EXIT
log "vayu install -- logging to $LOG_FILE"

if [ -z "${VAYU_INSTALL_REEXEC:-}" ]; then
  # Asked (or the argument checked) before anything else, so a typo'd
  # channel fails in the first second, not after the upgrade.
  [ -d "$DOTFILES_DIR/.git" ] || choose_branch "${1:-}"
  run_step --critical "Preflight checks" preflight
  # Preflight asked for the password once; keep it fresh: AUR builds can
  # outlast sudo's 5-minute timeout, and a prompt mid-build would stall
  # an unattended run.
  MAIN_PID=$$
  ( { set +x; } 2>/dev/null; while kill -0 "$MAIN_PID" 2>/dev/null; do sudo -n -v 2>/dev/null; sleep 50; done ) &
  SUDO_KEEPALIVE_PID=$!
  run_step --critical "Installing prerequisites (keyring, full upgrade, git, stow, base-devel)" prerequisites
  run_step --critical "Syncing dotfiles repo ($DOTFILES_DIR)" sync_repo
  # Hand over to the repo's installer: the copy curl fetched comes from
  # main and may not match the checked-out branch's lists and layout.
  # Also when the pull just changed this very file: run the new one.
  if [ "$(realpath "${BASH_SOURCE[0]}" 2>/dev/null)" != "$(realpath "$DOTFILES_DIR/install.sh")" ] ||
     [ "$SELF_SUM" != "$(sha256sum < "$DOTFILES_DIR/install.sh")" ]; then
    log "Continuing with $DOTFILES_DIR/install.sh"
    trap - EXIT
    [ -n "${SUDO_KEEPALIVE_PID:-}" ] && kill "$SUDO_KEEPALIVE_PID" 2>/dev/null
    export VAYU_INSTALL_REEXEC=1 VAYU_RUN_START=$RUN_START VAYU_FAILURES_FILE=$FAILURES_FILE \
      VAYU_FAILED_STEPS=$FAILED_STEPS VAYU_STEP_RESULTS="$(printf '%s\n' "${STEP_RESULTS[@]}")"
    exec bash "$DOTFILES_DIR/install.sh" "$@"
  fi
else
  log "Continuing from the bootstrap copy (preflight, prerequisites and repo sync done)"
  sudo -v
  MAIN_PID=$$
  ( { set +x; } 2>/dev/null; while kill -0 "$MAIN_PID" 2>/dev/null; do sudo -n -v 2>/dev/null; sleep 50; done ) &
  SUDO_KEEPALIVE_PID=$!
fi

cd "$DOTFILES_DIR"
# shellcheck source=packages/manifest.sh
source "$DOTFILES_DIR/packages/manifest.sh"

run_step "Installing official packages (packages/pacman.txt)" install_official
# Before the AUR builds: system/ carries makepkg.conf.d (-j$(nproc), !debug).
run_step "Installing system files (system/ -> /)" apply_system_files
run_step --critical "Bootstrapping yay (AUR helper)" bootstrap_yay
run_step "Installing AUR packages (packages/aur.txt)" install_aur
run_step --critical "Stowing configs into ~ (conflicts backed up to $BACKUP_DIR)" stow_all
run_step "Installing the login screen (greetd + tuigreet, greeter/)" apply_greeter
run_step "Installing the boot splash (Plymouth, splash/)" apply_splash
run_step "Installing the AI tools (vayu-elevate, ai/)" apply_ai
run_step "Setting up zsh (default shell, oh-my-zsh, theme, plugins)" setup_shell
run_step "Setting up tmux plugins (TPM)" setup_tmux
run_step "Installing Neovim plugins (lazy.nvim)" setup_nvim
run_step "Enabling corepack (pnpm, yarn)" setup_node
run_step "Installing Homebrew + formulae (${BREW_FORMULAE[*]})" setup_brew
run_step "Registering Claude Code hooks" setup_claude_hooks
run_step "Enabling system services, masks and firewall" setup_system_services
run_step "Adding $USER to groups (${USER_GROUPS[*]})" setup_groups
run_step "Enabling user services" setup_user_services
run_step "Applying GTK theme (dconf)" apply_theme
run_step "Fetching the first wallpaper" first_wallpaper
run_step "Verifying the result (vayu-verify)" verify
