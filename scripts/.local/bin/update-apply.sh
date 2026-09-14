#!/usr/bin/env bash
# Applies the update update-check.sh found -- pull, restow, reload live
# state. Only ever invoked by the "Update Now" button in
# nwg-bar/.config/nwg-bar/update-bar.json, never run standalone as part
# of the check itself, so a user who clicks "Later" (or ignores the
# prompt) never has this touch anything.
#
# --ff-only, deliberately: this must never merge, rebase, or otherwise
# rewrite history on its own. If HEAD has local commits @{u} doesn't
# know about (this machine's own feature branches earlier today, for
# instance) or something local has genuinely diverged, --ff-only just
# refuses and this reports that back rather than silently picking a
# resolution strategy for you.
set -uo pipefail

DOTFILES_DIR="$HOME/dotfiles"
LOG_DIR="$HOME/.local/state/update-check"
LOG_FILE="$LOG_DIR/update-check.log"
mkdir -p "$LOG_DIR"

log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG_FILE"; }

ICON_ERROR=/usr/share/icons/Papirus/48x48/status/dialog-error.svg
ICON_OK=/usr/share/icons/Papirus/48x48/apps/system-software-update.svg

cd "$DOTFILES_DIR" || {
    notify-send -u critical -i "$ICON_ERROR" "Update failed" "$DOTFILES_DIR not found"
    exit 1
}

BRANCH=$(git rev-parse --abbrev-ref HEAD)

if ! PULL_OUT=$(timeout 30 git -c core.sshCommand="ssh -o BatchMode=yes -o ConnectTimeout=8" pull --ff-only origin "$BRANCH" 2>&1); then
    log "pull --ff-only failed: $PULL_OUT"
    notify-send -u critical -i "$ICON_ERROR" "Update failed" \
        "git pull --ff-only on $BRANCH didn't fast-forward -- check ~/dotfiles for local changes or a diverged branch, then resolve manually"
    exit 1
fi
log "pulled: $PULL_OUT"

# Same package discovery install.sh itself uses (every top-level dir
# except packages/docs/hidden ones) -- restow (-R, not plain stow) so
# both new files in the pull AND anything removed get their symlinks
# corrected, not just newly-added ones.
mapfile -t PKGS < <(find . -maxdepth 1 -mindepth 1 -type d ! -name packages ! -name docs ! -name '.*' -printf '%f\n')
if ! STOW_OUT=$(stow -R -d "$DOTFILES_DIR" -t "$HOME" "${PKGS[@]}" 2>&1); then
    log "stow -R failed: $STOW_OUT"
    notify-send -u critical -i "$ICON_ERROR" "Update pulled but restow failed" \
        "git pull succeeded but 'stow -R' hit a conflict -- run it manually in ~/dotfiles to see what's blocking it"
    exit 1
fi
log "restowed: ${PKGS[*]}"

# Reload what can hot-reload; systemd units get their definitions
# refreshed but are deliberately NOT restarted here -- guessing which
# service changed and bouncing it automatically risks doing that to
# something disruptive (mid-notification, mid-suspend-hook, etc.).
# Told explicitly below instead: log out/reboot for those to actually
# take effect, same as any other systemd unit-file edit on this system.
swaymsg reload >/dev/null 2>&1 || true
makoctl reload >/dev/null 2>&1 || true
systemctl --user daemon-reload >/dev/null 2>&1 || true

log "update applied successfully on $BRANCH"
notify-send -u normal -i "$ICON_OK" "Desktop updated" \
    "Pulled and restowed the latest $BRANCH. Sway/mako reloaded live -- log out or reboot if any systemd service definitions changed."
