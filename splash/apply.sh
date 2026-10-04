#!/usr/bin/env bash
# Installs the Vayu boot splash: Plymouth with the theme in theme/ (the logo
# writes itself, then a light runs along the wind line) instead of kernel
# and systemd text between the firmware logo and the login screen. Run as
# your user; it calls sudo. Takes effect at the next boot.
#
#   splash/apply.sh          install whatever differs, then rebuild the UKI
#   splash/apply.sh --check  list what differs, exit 1 if anything does
#
# Rollback: see splash/README.md.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
check=false
[ "${1:-}" = "--check" ] && check=true

themes=/usr/share/plymouth/themes
# Kernel options: quiet + splash hand the console to Plymouth; the log
# levels keep the few remaining kernel/udev lines off it. Without
# plymouth.use-simpledrm, Plymouth ignores the firmware framebuffer and
# waits for amdgpu, which (no kms hook, see system/apply.sh) only loads
# from the root filesystem: the first ~2 s would be a blank screen.
cmdline_opts=(quiet splash loglevel=3 rd.udev.log_level=3 plymouth.use-simpledrm)

changed=()
differs() { changed+=("$1"); if $check; then echo "differs: $1"; fi; }

if ! pacman -Q plymouth >/dev/null 2>&1; then
  differs "plymouth is not installed"
  $check || sudo pacman -S --needed --noconfirm plymouth
fi

# Theme files, plus removing any the repo no longer has (old frames).
# Reported as one line: the frames alone are 116 files.
stale=0
for src in "$here"/theme/*; do
  dst="$themes/vayu/$(basename "$src")"
  cmp -s "$src" "$dst" 2>/dev/null && continue
  stale=$((stale + 1))
  $check || sudo install -Dm644 "$src" "$dst"
done
for dst in "$themes"/vayu/*; do
  [ -e "$dst" ] || continue
  [ -e "$here/theme/$(basename "$dst")" ] && continue
  stale=$((stale + 1))
  $check || sudo rm -f "$dst"
done
[ "$stale" -gt 0 ] && differs "$themes/vayu ($stale file(s) differ from splash/theme/)"

if ! cmp -s "$here/plymouthd.conf" /etc/plymouth/plymouthd.conf 2>/dev/null; then
  differs /etc/plymouth/plymouthd.conf
  $check || sudo install -Dm644 "$here/plymouthd.conf" /etc/plymouth/plymouthd.conf
fi

# The plymouth hook goes right after udev (Plymouth needs udev to find the
# display), as the Arch wiki has it.
if ! grep -qE '^HOOKS=\(.*\bplymouth\b' /etc/mkinitcpio.conf; then
  differs "/etc/mkinitcpio.conf (no plymouth hook)"
  $check || sudo sed -i -E '/^HOOKS=/s/\budev\b/udev plymouth/' /etc/mkinitcpio.conf
fi

# /etc/kernel/cmdline also holds per-machine options (root=), so the splash
# options are appended in place rather than shipping a copy.
missing=()
if [ ! -f /etc/kernel/cmdline ]; then
  echo "warning: no /etc/kernel/cmdline (not a UKI setup?); add to the kernel command line by hand: ${cmdline_opts[*]}" >&2
else for opt in "${cmdline_opts[@]}"; do
  grep -qE "(^| )$opt( |$)" /etc/kernel/cmdline || missing+=("$opt")
done; fi
if [ "${#missing[@]}" -gt 0 ]; then
  differs "/etc/kernel/cmdline (missing: ${missing[*]})"
  $check || sudo sed -i "1s/\$/ ${missing[*]}/" /etc/kernel/cmdline
fi

if $check; then
  [ "${#changed[@]}" -eq 0 ] && echo "boot splash matches the repo"
  [ "${#changed[@]}" -eq 0 ]
  exit
fi
[ "${#changed[@]}" -eq 0 ] && { echo "boot splash already up to date"; exit 0; }

# The theme, the hook and the command line all live inside the UKI.
sudo mkinitcpio -P
echo "Boot splash installed: ${#changed[@]} change(s). Reboot to see it."
