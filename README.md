# 🌬️ Vayu

*Named after the Hindu god of wind -- Sway tiles and moves windows the same way air moves, and "sway" itself means exactly that.*

🌐 **[Browse the full docs site →](https://theyashsawarkar.github.io/vayu/)**
(this same README, plus [CHANGELOG.md](CHANGELOG.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md),
and [docs/VERSIONING.md](docs/VERSIONING.md) -- built from this repo directly, not a separate
copy to keep in sync.)

A minimal, keyboard-driven Arch Linux desktop built around Wayland, Sway, and modern terminal-based development tools.

This repository contains the complete configuration for my daily development environment, managed with GNU Stow for reproducible setup and easy maintenance.

---

## ⚡ Quick Start (fresh Arch install)

After `archinstall` finishes, reboot, log in on the TTY as your normal user, make
sure networking is up (`iwctl` if it's Wi-Fi), and run:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Theyashsawarkar/vayu/main/install.sh)
```

This installs every package (`packages/pacman.txt` + `packages/aur.txt`, bootstrapping
`yay` if needed), stows every config in this repo, sets up zsh (oh-my-zsh, Powerlevel10k,
plugins), tmux (TPM), the Nerd Font the status bars need, Homebrew (`gh`, `pnpm`), and
enables the required services. It backs up any pre-existing conflicting dotfiles to
`~/.dotfiles-backup` before stowing, and is safe to re-run.

When it finishes: reboot, log in at the tuigreet prompt on tty1 (it starts Sway), and
inside a tmux pane press `prefix + I` (`Ctrl-a` then `Shift-i`) once to fetch the tmux
plugins.

Secrets (API keys, tokens) are never in this repo — see
[Local Configuration](#-local-configuration) below for where those go after a fresh install.

📖 **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** explains how the stow packages map
to `$HOME`, what `install.sh` does step by step, and what's deliberately excluded.
**[CHANGELOG.md](CHANGELOG.md)** is the detailed log of what changed and why.

---

## ✨ Features

* ⚡ Lightweight Wayland desktop
* ⌨️ Keyboard-first workflow
* 🖥️ Sway window manager
* 📊 Waybar status bar
* 🚀 Wofi application launcher
* 🔔 Mako notifications
* 🐱 Kitty terminal
* 📝 Neovim development environment
* 🔀 Tmux session management
* 🧠 Zed editor
* 🔗 GNU Stow-powered dotfile management

---

## 🖼️ Desktop Stack

### Wayland Environment

| Component            | Software |
| -------------------- | -------- |
| Window Manager       | Sway     |
| Status Bar           | Waybar   |
| Application Launcher | Wofi     |
| Notifications        | Mako     |
| Lock Screen          | swaylock |
| Wallpaper            | swaybg   |

### Development Environment

| Component       | Software |
| --------------- | -------- |
| Terminal        | Kitty    |
| Multiplexer     | Tmux     |
| Terminal Editor | Neovim   |
| GUI Editor      | Zed      |
| Shell           | Zsh      |

### Media

| Component     | Software                                          |
| -------------- | -------------------------------------------------- |
| Music Daemon   | MPD (real filesystem watcher, zero third-party API) |
| Music Client   | rmpc (TUI, Catppuccin Mocha themed, real compositor glass) |
| Search/Download | `music-search.py` (wofi-based, real thumbnails, yt-dlp) |

---

## 📂 Repository Structure

Each directory represents an independent package managed by GNU Stow.

```text
.
├── install.sh       # one-command bootstrap, see Quick Start above
├── packages/        # pacman.txt + aur.txt manifests (not a stow package)
├── gtk/             # GTK 3/4 settings.ini (Catppuccin Mocha theme)
├── kitty/
├── mako/
├── mpd/             # MPD daemon config (music_directory, auto_update)
├── networkmanager-dmenu/  # wofi-backed Wi-Fi picker (scan/connect/toggle)
├── nvim/
├── nwg-bar/         # power menu (lock/logout/suspend/reboot/shutdown)
├── rmpc/            # MPD TUI client + Catppuccin Mocha theme
├── scripts/         # ~/.local/bin utilities used by sway keybindings
├── sway/
├── systemd/         # ~/.config/systemd/user units (wallpaper, swayidle,
│                    #   audio-idle-inhibit, batsignal, tmux)
├── tmux/
├── waybar/
├── wofi/
├── xdg/             # mimeapps.list (default app associations)
├── zed/
└── zsh/
```

The internal structure mirrors the target layout inside `$HOME`, allowing Stow to create symlinks automatically.

---

## 📦 Prerequisites

Install the required packages before bootstrapping the configuration.

```bash
sudo pacman -S git stow
```

---

## 🚀 Installation

### Clone the Repository

```bash
git clone https://github.com/Theyashsawarkar/vayu.git ~/dotfiles
cd ~/dotfiles
```

### Install Packages Manually (optional)

If you'd rather install packages yourself instead of running `install.sh`:

```bash
sudo pacman -S --needed - < packages/pacman.txt
yay -S --needed - < packages/aur.txt
```

### Stow Packages

Install individual packages:

```bash
stow kitty tmux nvim zed zsh scripts systemd gtk xdg
stow sway waybar mako wofi nwg-bar networkmanager-dmenu
stow mpd rmpc
```

Or install everything (`packages/` and `docs/` aren't stow packages, so they're excluded):

```bash
stow $(find . -maxdepth 1 -mindepth 1 -type d ! -name packages ! -name docs ! -name '.*' -printf '%f\n')
```

### Tmux Setup

The tmux config needs one thing Stow can't set up for you, and one plugin manager bootstrap:

* **Nerd Font** — the status bar's rounded separators and icons (session, docker) are
  Nerd Font glyphs. This repo standardizes on `JetBrainsMono Nerd Font` (a pacman
  package, `ttf-jetbrains-mono-nerd`, already in `packages/pacman.txt`) — install it and
  set it as your terminal's font. Without it, those glyphs render as blank boxes.
* **TPM (Tmux Plugin Manager)** — installs `tmux-resurrect` and `tmux-continuum`:

  ```bash
  git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
  ```

  Then inside a tmux session, press `prefix + I` (`Ctrl-a` then `Shift-i`) to install the plugins.

---

## 🔧 Managing Configurations

### Add a New Package

Create a package:

```bash
mkdir -p newpkg/.config/newpkg
```

Move the configuration:

```bash
mv ~/.config/newpkg/* newpkg/.config/newpkg/
```

Create symlinks:

```bash
stow newpkg
```

### Remove a Package

```bash
stow -D <package-name>
```

Example:

```bash
stow -D nvim
```

---

## 🔒 Local Configuration

Machine-specific settings, secrets, API tokens, and private paths should never be committed.

Create local override files and source them from the main configuration.

Examples:

```text
~/.zshrc.local
~/.gitconfig.local
~/.config/nvim/lua/local.lua
```

Add these files to `.gitignore`.

---

## 🎯 Goals

This setup prioritizes:

* Simplicity
* Performance
* Reproducibility
* Maintainability
* Keyboard-centric workflows

---

## 📸 Screenshots

Add screenshots here to showcase the desktop environment.

```markdown
![Desktop](./assets/desktop.png)
![Neovim](./assets/nvim.png)
```

---

## 🤝 Contributing

This repository is primarily maintained for personal use, but ideas, suggestions, and improvements are always welcome.

---

## 📄 License

MIT License
