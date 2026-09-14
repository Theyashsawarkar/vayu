#!/usr/bin/env bash
# Checks GitHub for new commits on whatever branch is currently checked
# out in ~/dotfiles, and if there are any, notifies and shows a
# nwg-bar prompt (Update Now / Later) to apply them. Run once per login
# via systemd/.config/systemd/user/update-check.service, not on every
# sway reload -- this is a startup check, not something that should
# re-fire every time the config gets edited and reloaded during a
# session.
#
# BatchMode=yes + a short ConnectTimeout on the fetch: this runs
# headless at login with no TTY to prompt on, so an SSH agent that
# somehow isn't up yet must fail fast, not hang the whole check
# indefinitely -- confirmed live that the real auth path (gpg-agent's
# SSH support, already running as a user service) works fine
# non-interactively, so this is a safety net for an edge case, not
# routinely needed.
#
# `@{u}` (the configured upstream for the checked-out branch) rather
# than a hardcoded branch name -- this machine's own `development`
# tracks `origin/development`, but hardcoding that would silently stop
# checking the right thing the moment `main` (or any other branch) is
# checked out instead. A branch with no upstream configured (a
# throwaway local branch, say) has nothing meaningful to compare
# against -- skipped cleanly, not an error.
#
# "Stable"/"Nightly" in the notification/prompt below are derived
# straight from the branch name (main -> Stable, development ->
# Nightly), not read from a separate channel-preference file --
# install.sh's own channel prompt only ever decides which branch gets
# checked out in the first place (see docs/VERSIONING.md's "Update
# channels" section), so the branch actually on disk already *is* the
# persisted choice. Nothing else needs to remember it separately.
set -uo pipefail

DOTFILES_DIR="$HOME/dotfiles"
LOG_DIR="$HOME/.local/state/update-check"
LOG_FILE="$LOG_DIR/update-check.log"
mkdir -p "$LOG_DIR"

log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG_FILE"; }

cd "$DOTFILES_DIR" || { log "ERROR: $DOTFILES_DIR not found"; exit 1; }

if ! timeout 20 git -c core.sshCommand="ssh -o BatchMode=yes -o ConnectTimeout=8" fetch origin --quiet 2>>"$LOG_FILE"; then
    log "fetch failed (offline, or auth not ready yet) -- skipping this boot"
    exit 0
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null) || {
    log "no upstream tracking branch for '$BRANCH' -- nothing to compare against"
    exit 0
}

COUNT=$(git rev-list "HEAD..@{u}" --count)
if [ "$COUNT" -eq 0 ]; then
    log "up to date with $UPSTREAM"
    exit 0
fi

# Real check, not just "any difference": HEAD..@{u} counts commits
# reachable from upstream but not from HEAD, i.e. genuinely new commits
# to pull -- if HEAD is instead *ahead* (local commits not yet pushed,
# same situation this repo's own feature branches were in for most of
# today's session), that count is 0 and this correctly stays quiet
# rather than prompting to "update" onto something older.
LATEST_SUBJECT=$(git log -1 --format=%s "@{u}")

case "$BRANCH" in
    main) CHANNEL="Stable" ;;
    development) CHANNEL="Nightly" ;;
    *) CHANNEL="$BRANCH" ;;
esac

log "$COUNT new commit(s) on $BRANCH ($CHANNEL), latest: $LATEST_SUBJECT"

PLURAL_S=""
[ "$COUNT" -ne 1 ] && PLURAL_S="s"

notify-send -u normal \
    -i /usr/share/icons/candy-icons/apps/scalable/system-software-update.svg \
    "Desktop update available ($CHANNEL)" \
    "$COUNT new commit$PLURAL_S -- latest: \"$LATEST_SUBJECT\""

nwg-bar -t "$HOME/.config/nwg-bar/update-bar.json" -s "$HOME/.config/nwg-bar/update-bar-style.css" -i 40
