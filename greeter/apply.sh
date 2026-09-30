#!/usr/bin/env bash
# Installs the tuigreet login screen (Mocha Rosé) system-wide. Run as your
# user; it calls sudo. Takes effect the next time greetd starts the greeter
# (reboot, or log out of sway). Rollback: see greeter/README.md.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
fonts=/usr/share/kbd/consolefonts

pacman -Q terminus-font >/dev/null 2>&1 || sudo pacman -S --needed --noconfirm terminus-font

# Rounded corners + icons: a patched copy of Terminus 12x24.
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
python3 "$here/build-console-font.py" "$fonts/ter-v24n.psf.gz" "$tmp"
sudo install -Dm644 "$tmp" "$fonts/ter-v24n-ace.psf.gz"

sudo install -Dm644 "$here/config.toml" /etc/tuigreet/config.toml
sudo install -Dm755 "$here/tuigreet-launch" /usr/local/bin/tuigreet-launch
sudo install -Dm644 "$here/vtrgb" /etc/vtrgb
sudo install -Dm644 "$here/vt-palette.service" /etc/systemd/system/vt-palette.service

# Console font for every tty (systemd-vconsole-setup reads this at boot).
if grep -q '^FONT=' /etc/vconsole.conf 2>/dev/null; then
  sudo sed -i 's/^FONT=.*/FONT=ter-v24n-ace/' /etc/vconsole.conf
else
  echo 'FONT=ter-v24n-ace' | sudo tee -a /etc/vconsole.conf >/dev/null
fi
# The font is set while the initramfs runs (mkinitcpio's consolefont hook).
# systemd-vconsole-setup only reruns when a console device appears, which
# has already happened by then, so the initramfs must carry the new font.
sudo mkinitcpio -P

# The session command now lives in /etc/tuigreet/config.toml.
sudo tee /etc/greetd/config.toml >/dev/null <<'TOML'
[terminal]
vt = 1

[default_session]
command = "/usr/local/bin/tuigreet-launch"
user = "greeter"
TOML

sudo systemctl daemon-reload
sudo systemctl enable vt-palette.service
echo "Login screen installed. Reboot (or log out of sway) to see it."
