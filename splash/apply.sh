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
# levels keep the few remaining kernel/udev lines off it. On Raven APUs
# vayu-kms (below) has amdgpu up before Plymouth starts; elsewhere, and if
# amdgpu ever fails, plymouth.use-simpledrm lets Plymouth draw on the
# firmware framebuffer instead of showing a blank screen.
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

# The plymouth hook goes after keymap/consolefont and before block (so
# before encrypt, if a machine has it). Plymouth puts the console in
# graphics mode, where setfont fails: placed before consolefont, the console
# font was skipped and only applied once tuigreet was already up, which
# re-laid it out on screen. Plymouth only needs udev to have run first.
mapfile -t hooks < <(sed -nE 's/^HOOKS=\((.*)\)/\1/p' /etc/mkinitcpio.conf | tr -s ' ' '\n' | grep .)
want=() placed=false
for h in "${hooks[@]}"; do
  [ "$h" = plymouth ] && continue
  if ! $placed && [[ $h =~ ^(block|sd-encrypt|encrypt|filesystems)$ ]]; then want+=(plymouth); placed=true; fi
  want+=("$h")
done
$placed || want+=(plymouth)
if [ "${hooks[*]}" != "${want[*]}" ]; then
  differs "/etc/mkinitcpio.conf (HOOKS should be: ${want[*]})"
  $check || sudo sed -i -E "s/^HOOKS=.*/HOOKS=(${want[*]})/" /etc/mkinitcpio.conf
fi

# Early KMS for AMD Raven-family APUs (this laptop): see initcpio/install/
# vayu-kms. Hardware-specific (the firmware list), so other machines get
# nothing here and any copy is removed.
kms_files=(
  "initcpio/install/vayu-kms:/etc/initcpio/install/vayu-kms"
  "initcpio/hooks/vayu-kms:/etc/initcpio/hooks/vayu-kms"
  "mkinitcpio-vayu-kms.conf:/etc/mkinitcpio.conf.d/vayu-kms.conf"
)
raven=false
for d in /sys/bus/pci/devices/*; do
  [ "$(cat "$d/vendor" 2>/dev/null)" = 0x1002 ] || continue
  case $(cat "$d/device" 2>/dev/null) in 0x15d8|0x15dd) raven=true ;; esac
done
for pair in "${kms_files[@]}"; do
  src=$here/${pair%%:*} dst=${pair#*:}
  if $raven; then
    cmp -s "$src" "$dst" 2>/dev/null && continue
    differs "$dst"
    $check || sudo install -Dm644 "$src" "$dst"
  elif [ -e "$dst" ]; then
    differs "$dst (only for Raven-family APUs; remove)"
    $check || sudo rm -f "$dst"
  fi
done

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
