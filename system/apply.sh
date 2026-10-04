#!/usr/bin/env bash
# Installs the root-owned files under system/ to the same path under /
# (system/etc/foo -> /etc/foo). Not a stow package: these must be real
# root-owned files (system-sleep hooks, PAM and logind only read /etc),
# not links into a user's home. Run as your user; it calls sudo.
#
#   system/apply.sh          install whatever differs, then reload it
#   system/apply.sh --check  list what differs from the repo, exit 1 if any
#
# Modes come from the repo: executable files go in 755, the rest 644.
# Small edits to package-owned files (pacman.conf) are made in place
# below rather than shipping a copy, since those files also carry
# per-machine settings.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
check=false
[ "${1:-}" = "--check" ] && check=true

mapfile -t files < <(cd "$here" && find etc -type f | sort)

changed=()
# Live reloads are a bonus (see the end); a failed one warns, never fails.
reload() { "$@" || echo "warning: '$*' failed; the change applies at the next reboot" >&2; }
for rel in "${files[@]}"; do
  src="$here/$rel" dst="/$rel"
  mode=644; [ -x "$src" ] && mode=755
  if cmp -s "$src" "$dst" 2>/dev/null && [ "$(stat -c %a "$dst")" = "$mode" ]; then
    continue
  fi
  changed+=("$rel")
  if $check; then
    echo "differs: /$rel"
  else
    sudo install -Dm"$mode" "$src" "$dst"
    echo "installed /$rel ($mode)"
  fi
done

# Leftovers that override the repo's files: removed only while they still
# hold exactly the old content, so a file someone has since edited is
# reported, never deleted. Format: "path|exact content".
#   99-sysctl.conf: a hand-made swappiness=10 from before system/ existed.
#   Sorting after 99-custom.conf, it silently won over vm.swappiness=180.
retired=(
  "/etc/sysctl.d/99-sysctl.conf|vm.swappiness=10"
)
for r in "${retired[@]}"; do
  f=${r%%|*} want=${r#*|}
  [ -e "$f" ] || continue
  if [ "$(cat "$f")" = "$want" ]; then
    changed+=("${f#/} (retired)")
    if $check; then
      echo "differs: $f is a leftover that overrides the repo (to be removed)"
    else
      sudo rm -f "$f"
      echo "removed leftover $f"
    fi
  else
    echo "warning: $f exists but no longer holds the known leftover content; check it by hand" >&2
  fi
done

# Wi-Fi regulatory country (wireless-regdb's /etc/conf.d/wireless-regdom,
# read by its udev rule at boot). Unset, the kernel stays on the "world"
# domain (00): fewer 5 GHz channels and lower transmit power.
regdom=IN
if [ -f /etc/conf.d/wireless-regdom ] && ! grep -qx "WIRELESS_REGDOM=\"$regdom\"" /etc/conf.d/wireless-regdom; then
  changed+=("wireless-regdom $regdom")
  if $check; then
    echo "differs: /etc/conf.d/wireless-regdom (WIRELESS_REGDOM=\"$regdom\" not set)"
  else
    sudo sed -i -e 's/^WIRELESS_REGDOM=/#&/' -e "s/^#WIRELESS_REGDOM=\"$regdom\"/WIRELESS_REGDOM=\"$regdom\"/" /etc/conf.d/wireless-regdom
    reload sudo set-wireless-regdom
    echo "set Wi-Fi regulatory country $regdom in /etc/conf.d/wireless-regdom"
  fi
fi

# Initramfs size. The kms hook packs the GPU driver plus firmware for every
# chip it supports; for amdgpu that made the UKI ~47 MB unpacked, which the
# firmware reads slowly off the ESP (~5.8 s "loader" in systemd-analyze).
# Without it the driver loads from the root filesystem a moment later, and
# systemd-vconsole-setup reapplies the console font when it does. The
# preset's --splash only paints a logo during that wait, so it goes too.
# (splash/apply.sh's vayu-kms hook brings amdgpu back early with only this
# APU's firmware, ~6 MB instead of ~35 MB.)
rebuild_initramfs=false
if grep -qE '^HOOKS=\(.*\bkms\b' /etc/mkinitcpio.conf 2>/dev/null; then
  changed+=("mkinitcpio kms hook")
  if $check; then
    echo "differs: /etc/mkinitcpio.conf (kms hook still in HOOKS)"
  else
    sudo sed -i -E '/^HOOKS=/{s/ kms\b//;s/\(kms /(/}' /etc/mkinitcpio.conf
    echo "removed the kms hook from /etc/mkinitcpio.conf"
    rebuild_initramfs=true
  fi
fi
for preset in /etc/mkinitcpio.d/*.preset; do
  grep -qE '^[a-z]+_options=.*--splash' "$preset" 2>/dev/null || continue
  changed+=("$(basename "$preset") splash")
  if $check; then
    echo "differs: $preset (UKI boot splash still set)"
  else
    sudo sed -i -E '/^[a-z]+_options=/s/ ?--splash [^ "]+//' "$preset"
    echo "removed the boot splash from $preset"
    rebuild_initramfs=true
  fi
done
if $rebuild_initramfs; then sudo mkinitcpio -P; fi

# pacman.conf: coloured output, as on the original machine.
if ! grep -qx 'Color' /etc/pacman.conf; then
  changed+=("pacman.conf Color")
  if $check; then
    echo "differs: /etc/pacman.conf (Color not enabled)"
  else
    sudo sed -i 's/^#Color$/Color/' /etc/pacman.conf
    grep -qx 'Color' /etc/pacman.conf || sudo sed -i '/^\[options\]/a Color' /etc/pacman.conf
    echo "enabled Color in /etc/pacman.conf"
  fi
fi

if $check; then
  [ "${#changed[@]}" -eq 0 ] && echo "system files match the repo"
  [ "${#changed[@]}" -eq 0 ]
  exit
fi

[ "${#changed[@]}" -eq 0 ] && { echo "system files already up to date"; exit 0; }

# Reload what changed. zram-generator only acts at boot, so its config
# takes effect on the next reboot.
# Live reloads are a bonus: the files are what count, and all of them apply
# at the next boot anyway. So a failed reload warns rather than fails.
printf '%s\n' "${changed[@]}" | grep -q '^etc/sysctl.d/' && reload sudo sysctl --system >/dev/null
printf '%s\n' "${changed[@]}" | grep -q '^etc/systemd/' && reload sudo systemctl daemon-reload
if printf '%s\n' "${changed[@]}" | grep -q '^etc/systemd/logind.conf.d/'; then
  # HUP makes logind re-read its config without ending any session.
  reload sudo systemctl kill -s HUP systemd-logind.service
fi
if printf '%s\n' "${changed[@]}" | grep -q '^etc/systemd/journald.conf.d/'; then
  reload sudo systemctl restart systemd-journald.service
fi
echo "system files applied: ${#changed[@]} change(s)"
