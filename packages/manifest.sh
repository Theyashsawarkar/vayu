# Sourced (not run) by install.sh and vayu-verify: everything about this
# system that isn't a package list or a file -- services, masks, groups,
# user-level tools. One list for both, so what gets set up and what gets
# checked can't drift apart. Package lists stay in pacman.txt / aur.txt.

# System units enabled and started now.
SYSTEM_UNITS_NOW=(
  NetworkManager.service
  bluetooth.service
  docker.socket             # docker starts on first use, not at boot
  power-profiles-daemon.service
  systemd-oomd.service
  systemd-timesyncd.service
  fstrim.timer
  ufw.service
  paccache.timer            # weekly: keep the last 3 versions in pacman's cache
  systemd-boot-update.service  # copies a newer systemd-boot to the ESP at boot
)
# System units enabled only: they take over the console (greetd) or only
# matter at boot (vt-palette, enabled by greeter/apply.sh).
SYSTEM_UNITS_ENABLE=(
  greetd.service
  vt-palette.service
)
# Must stay disabled (docker.service pulled NetworkManager-wait-online into
# every boot; sddm is the login manager greetd replaced).
SYSTEM_UNITS_DISABLED=(
  docker.service
  sddm.service
)
# Hibernate corrupts the amdgpu resume on this hardware (docs/ARCHITECTURE.md,
# "Lid-close, suspend vs hibernate"); NvPCR units fail without a systemd
# initramfs.
SYSTEM_UNITS_MASKED=(
  systemd-hibernate.service systemd-hybrid-sleep.service
  systemd-suspend-then-hibernate.service hibernate.target hybrid-sleep.target
  suspend-then-hibernate.target
  systemd-tpm2-setup-early.service systemd-pcrproduct.service
  systemd-pcrlogin@.service
)

# User units enabled and started now.
USER_UNITS_NOW=(
  wallpaper.timer
  tmux-autosave.timer
  batsignal.service
  battery-warning-dismiss.service
  battery-limit-watch.service
  mpd.service               # rmpc's music daemon
  ydotool.service           # ydotoold, for ydotool key/type in pickers
)
# User units enabled only: they start with sway (WantedBy=sway-session.target).
# swayidle, swaylock-on-sleep and sway-audio-idle-inhibit are started by
# sway's own config, so they're not listed.
USER_UNITS_ENABLE=(
  update-check.service
)

# Directories under ~ that must be real directories, never stow "folded"
# links into the repo. Stow links a whole directory when it doesn't exist
# yet, which on a fresh machine meant everything apps write there went
# into ~/dotfiles: nvim's plugins via ~/.local/share, systemctl --user's
# .wants links via ~/.config/systemd/user, Claude Code's settings via
# ~/.claude, TPM plugins via ~/.tmux, GTK bookmarks via gtk-3.0. Taken
# from this machine, where they were real because they existed first.
STOW_REAL_DIRS=(
  .claude
  .config .config/gtk-3.0 .config/gtk-4.0 .config/systemd .config/systemd/user
  .local .local/bin .local/share .local/state
  .tmux .tmux/scripts
)

# Supplementary groups for the installing user.
#   docker  run docker without sudo
#   input   /dev/uinput, which ydotoold needs (ydotool's 80-uinput.rules)
USER_GROUPS=(docker input)

# Firewall: ufw denies incoming by default; KDE Connect needs these.
UFW_ALLOW=(1714:1764/udp 1714:1764/tcp)

# Homebrew formulae (gh lives here rather than as github-cli).
BREW_FORMULAE=(gh)

# zsh plugins/theme cloned into oh-my-zsh's custom dir: "url dest".
ZSH_CLONES=(
  "https://github.com/romkatv/powerlevel10k.git themes/powerlevel10k"
  "https://github.com/zsh-users/zsh-autosuggestions plugins/zsh-autosuggestions"
  "https://github.com/zsh-users/zsh-syntax-highlighting.git plugins/zsh-syntax-highlighting"
)

# GTK theme as GNOME-aware apps read it (dconf), on top of settings.ini.
DCONF_SETTINGS=(
  "/org/gnome/desktop/interface/gtk-theme 'catppuccin-mocha-mauve-standard+default'"
  "/org/gnome/desktop/interface/color-scheme 'prefer-dark'"
  "/org/gnome/desktop/interface/icon-theme 'candy-icons'"
)
