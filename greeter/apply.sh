#!/usr/bin/env bash
# Installs the tuigreet login screen (Mocha Rosé) system-wide. Run as your
# user; it calls sudo. Takes effect the next time greetd starts the greeter
# (reboot, or log out of sway). Rollback: see greeter/README.md.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
fonts=/usr/share/kbd/consolefonts

pacman -Q terminus-font >/dev/null 2>&1 || sudo pacman -S --needed --noconfirm terminus-font
command -v cargo >/dev/null || sudo pacman -S --needed --noconfirm rust  # builds tuigreet-ace

# Rounded corners: a patched copy of Terminus 12x24. The initramfs only
# needs rebuilding (below) when the font or the FONT= line changes.
tmp=$(mktemp) build=$(mktemp -d)
trap 'rm -rf "$tmp" "$build"' EXIT
rebuild_initramfs=false
python3 "$here/build-console-font.py" "$fonts/ter-v24n.psf.gz" "$tmp"
if ! cmp -s <(zcat "$tmp") <(zcat "$fonts/ter-v24n-ace.psf.gz" 2>/dev/null); then
  sudo install -Dm644 "$tmp" "$fonts/ter-v24n-ace.psf.gz"
  rebuild_initramfs=true
fi

# Launcher and greetd config first, before the ~3 min tuigreet-ace build:
# tuigreet-launch falls back to stock tuigreet, so if the build below fails
# the next boot still gets a working login screen.
sudo install -Dm644 "$here/config.toml" /etc/tuigreet/config.toml
sudo install -Dm755 "$here/tuigreet-launch" /usr/local/bin/tuigreet-launch
sudo install -Dm644 "$here/vtrgb" /etc/vtrgb
sudo install -Dm644 "$here/vt-palette.service" /etc/systemd/system/vt-palette.service
sudo mkdir -p /etc/greetd
# The session command lives in /etc/tuigreet/config.toml.
sudo tee /etc/greetd/config.toml >/dev/null <<'TOML'
[terminal]
vt = 1

[default_session]
command = "/usr/local/bin/tuigreet-launch"
user = "greeter"
TOML

# tuigreet-ace: tuigreet with the box centred on the screen instead of lifted
# by window_padding (tuigreet-center-box.patch). A separate binary, so a
# pacman update of greetd-tuigreet doesn't undo it; tuigreet-launch falls
# back to stock tuigreet if it's missing.
# The stamp records what was built, so a re-run skips the ~3 min build.
tg_ver=0.11.1
tg_sha=7d643ba224c40c6a63f9462a826630543071aea08e732ccd2e880bcd80d939e8
stamp=/usr/local/share/tuigreet-ace/build-id
build_id="$tg_ver $(sha256sum < "$here/tuigreet-center-box.patch" | cut -d' ' -f1)"
if [ -x /usr/local/bin/tuigreet-ace ] && [ "$(cat "$stamp" 2>/dev/null)" = "$build_id" ]; then
  echo "tuigreet-ace $tg_ver is up to date."
else
  curl -fsSL "https://github.com/tuigreet/tuigreet/archive/$tg_ver/tuigreet-$tg_ver.tar.gz" -o "$build/src.tar.gz"
  echo "$tg_sha  $build/src.tar.gz" | sha256sum -c --quiet
  tar -xzf "$build/src.tar.gz" -C "$build"
  patch -d "$build/tuigreet-$tg_ver" -p1 --forward < "$here/tuigreet-center-box.patch"
  cargo build --locked --release --manifest-path "$build/tuigreet-$tg_ver/Cargo.toml" \
    --target-dir "$build/target"
  sudo install -Dm755 "$build/target/release/tuigreet" /usr/local/bin/tuigreet-ace
  echo "$build_id" | sudo install -Dm644 /dev/stdin "$stamp"
fi


# Console font for every tty (systemd-vconsole-setup reads this at boot).
if ! grep -qx 'FONT=ter-v24n-ace' /etc/vconsole.conf 2>/dev/null; then
  if grep -q '^FONT=' /etc/vconsole.conf 2>/dev/null; then
    sudo sed -i 's/^FONT=.*/FONT=ter-v24n-ace/' /etc/vconsole.conf
  else
    echo 'FONT=ter-v24n-ace' | sudo tee -a /etc/vconsole.conf >/dev/null
  fi
  rebuild_initramfs=true
fi
# The font is set while the initramfs runs (mkinitcpio's consolefont hook).
# systemd-vconsole-setup only reruns when a console device appears, which
# has already happened by then, so the initramfs must carry the new font.
if $rebuild_initramfs; then sudo mkinitcpio -P; fi


sudo systemctl daemon-reload
sudo systemctl enable vt-palette.service
echo "Login screen installed. Reboot (or log out of sway) to see it."
