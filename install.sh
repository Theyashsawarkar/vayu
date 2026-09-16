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
# This is what the docs site's own two download buttons hand you -- the
# installer script itself always comes from `main` either way (the
# best-tested copy of install.sh), only which branch of the *dotfiles* gets
# cloned differs. Anything else passed as the argument is a hard error, not
# a silent fallback to Stable -- a typo here should be caught immediately,
# not quietly install the wrong channel.
#
# Idempotent: safe to re-run (e.g. after adding a package to packages/*.txt).

set -euo pipefail

DOTFILES_DIR="$HOME/dotfiles"
REPO_URL="https://github.com/Theyashsawarkar/vayu.git"
BACKUP_DIR="$HOME/.dotfiles-backup"

log() { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }

if [ "$(id -u)" -eq 0 ]; then
  echo "Run this as your normal user, not root (it calls sudo where needed)." >&2
  exit 1
fi

log "Installing prerequisites (git, stow, base-devel)"
sudo pacman -Sy --needed --noconfirm git stow base-devel

if [ -d "$DOTFILES_DIR/.git" ]; then
  log "Pulling latest dotfiles"
  git -C "$DOTFILES_DIR" pull --ff-only
else
  # Update channel: either handed directly as $1 (what the docs site's
  # own download buttons pass), or asked interactively here at first
  # install if not -- not re-asked on idempotent re-runs above, since
  # the branch is already decided by then. See docs/VERSIONING.md's
  # "Update channels" section: this is the only place the choice is
  # ever made -- scripts/.local/bin/update-check.sh (runs once per
  # login from here on) just reads whichever branch actually ends up
  # checked out, no separate preference file to keep in sync with this
  # one.
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
    # Explicit /dev/tty, not plain stdin: documented usage is
    # `bash <(curl -fsSL ...)` (process substitution, real terminal
    # stdin already), but reading from /dev/tty directly means this
    # still prompts correctly even for someone who runs it as
    # `curl ... | bash` instead, where stdin is genuinely the pipe --
    # rather than silently skipping straight to the default with no
    # chance to ask. `|| true` + the empty-string fallthrough below
    # cover the case where no controlling terminal exists at all
    # (fully non-interactive/CI-style invocation): falls through to
    # Stable, the same as just pressing Enter, never hangs waiting for
    # input that can't come.
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
  log "Cloning dotfiles repo ($BRANCH)"
  git clone -b "$BRANCH" "$REPO_URL" "$DOTFILES_DIR"
fi
cd "$DOTFILES_DIR"

# Every top-level dir except packages/ and docs/ (not stow packages)
mapfile -t PKGS < <(find . -maxdepth 1 -mindepth 1 -type d ! -name packages ! -name docs ! -name '.*' -printf '%f\n')

log "Installing official repo packages (packages/pacman.txt)"
xargs -a packages/pacman.txt sudo pacman -S --needed --noconfirm

if ! command -v yay >/dev/null 2>&1; then
  log "Bootstrapping yay (AUR helper)"
  tmp=$(mktemp -d)
  git clone https://aur.archlinux.org/yay.git "$tmp/yay"
  (cd "$tmp/yay" && makepkg -si --noconfirm)
  rm -rf "$tmp"
fi

log "Installing AUR packages (packages/aur.txt)"
xargs -a packages/aur.txt yay -S --needed --noconfirm

log "Backing up any pre-existing files that would conflict with stow"
mkdir -p "$BACKUP_DIR"
for pkg in "${PKGS[@]}"; do
  conflicts=$(stow -n -v -t "$HOME" "$pkg" 2>&1 || true)
  echo "$conflicts" | { grep -oE 'existing target \S+' || true; } | awk '{print $3}' | while read -r f; do
    target="$HOME/$f"
    if [ -e "$target" ] && [ ! -L "$target" ]; then
      mkdir -p "$BACKUP_DIR/$(dirname "$f")"
      mv "$target" "$BACKUP_DIR/$f"
      echo "  backed up ~/$f -> $BACKUP_DIR/$f"
    fi
  done
done

log "Stowing all packages"
stow -d "$DOTFILES_DIR" -t "$HOME" "${PKGS[@]}"

log "Setting zsh as the default shell"
if [ "$SHELL" != "$(command -v zsh)" ]; then
  chsh -s "$(command -v zsh)"
fi

log "Installing oh-my-zsh + plugins/theme"
if [ ! -d "$HOME/.oh-my-zsh" ]; then
  RUNZSH=no CHSH=no KEEP_ZSHRC=yes sh -c \
    "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
fi
ZSH_CUSTOM="$HOME/.oh-my-zsh/custom"
clone_if_missing() { [ -d "$2" ] || git clone --depth=1 "$1" "$2"; }
clone_if_missing https://github.com/romkatv/powerlevel10k.git "$ZSH_CUSTOM/themes/powerlevel10k"
clone_if_missing https://github.com/zsh-users/zsh-autosuggestions "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
clone_if_missing https://github.com/zsh-users/zsh-syntax-highlighting.git "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"

log "Installing TPM (tmux plugin manager)"
clone_if_missing https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"

# Nerd Font: ttf-jetbrains-mono-nerd is already in packages/pacman.txt, no
# manual download needed -- every config (kitty, tmux, sway, mako, wofi, zed,
# waybar) uses "JetBrainsMono Nerd Font" for exactly this reason.

if ! command -v brew >/dev/null 2>&1 && [ ! -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
  log "Installing Homebrew (for gh, pnpm)"
  NONINTERACTIVE=1 /bin/bash -c \
    "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
if [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"
  brew install gh pnpm
fi

log "Enabling system services"
# NetworkManager's actual wifi backend is wpa_supplicant (D-Bus-activated
# on demand, not enabled here directly) -- iwd is intentionally NOT enabled
# alongside it. Running both is redundant (two daemons that can each try to
# manage the wireless radio) and iwd would just sit there unused. See
# docs/ARCHITECTURE.md for how this was found on the original machine.
sudo systemctl enable --now \
  NetworkManager bluetooth docker power-profiles-daemon systemd-oomd
# ufw's default policy is deny-incoming/allow-outgoing once enabled; fine for
# a physical-console machine, but add any rules you need (e.g. `ufw allow ssh`)
# before enabling it if you plan to reach this box over the network.
sudo systemctl enable --now ufw
# sddm is enabled but not started now -- starting it mid-script would hijack
# this TTY session before the rest of the script finishes; it'll take over
# on the reboot the final instructions ask for.
sudo systemctl enable sddm

# Lid-close must suspend, never hibernate -- confirmed live on this exact
# machine (Acer Aspire A315-23, Ryzen 3250U/Vega APU) that hibernate resume
# corrupts the amdgpu firmware reload (RLC_RESTORE_LIST_* ucode fails to
# load, GPU reset then fails too) badly enough to force a hard power-cycle
# to recover -- see docs/ARCHITECTURE.md's "Lid-close, suspend vs
# hibernate" section for the full incident. Deep suspend (`/sys/power/
# mem_sleep` reports `s2idle [deep]` on this hardware) never hits that
# firmware-reload path at all, since the GPU state just stays powered in
# RAM instead of a full teardown/rebuild. Masking every hibernate-capable
# unit too, not just setting the lid action -- belt and suspenders against
# anything (a stray keybind, `systemctl hibernate` typed by habit) still
# reaching it.
log "Disabling hibernation, lid-close suspends only"
sudo mkdir -p /etc/systemd/logind.conf.d
sudo tee /etc/systemd/logind.conf.d/10-suspend-only.conf >/dev/null <<'EOF'
[Login]
HandleLidSwitch=suspend
HandleLidSwitchExternalPower=suspend
EOF
sudo systemctl mask systemd-hibernate.service systemd-hybrid-sleep.service \
  systemd-suspend-then-hibernate.service hibernate.target hybrid-sleep.target \
  suspend-then-hibernate.target
sudo systemctl kill -s HUP systemd-logind.service

log "Adding $USER to the docker group"
sudo usermod -aG docker "$USER"

log "Enabling user services"
systemctl --user daemon-reload
systemctl --user enable --now wallpaper.timer swayidle.service sway-audio-idle-inhibit.service batsignal.service battery-warning-dismiss.service battery-limit-watch.service update-check.service swaylock-on-sleep.service

log "Applying GTK/dconf theme (gtk-3.0/gtk-4.0 settings.ini already stowed)"
if command -v dconf >/dev/null 2>&1; then
  dconf write /org/gnome/desktop/interface/gtk-theme "'catppuccin-mocha-mauve-standard+default'"
  dconf write /org/gnome/desktop/interface/color-scheme "'prefer-dark'"
  dconf write /org/gnome/desktop/interface/icon-theme "'candy-icons'"
fi

log "Done."
echo "Reboot, log in through the SDDM greeter, and pick the Sway session."
echo "Inside a tmux session, press prefix + I (Ctrl-a then Shift-i) to fetch tmux plugins."
echo "Docker-group membership needs a fresh login (or 'newgrp docker') to take effect."
