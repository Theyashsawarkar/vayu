# Sourced (not run) by install.sh, vayu-verify, system/apply.sh and
# splash/apply.sh: the parts of this setup that depend on the CPU and GPU,
# detected on the machine itself so one repo works on any laptop.
# pacman.txt holds only hardware-independent packages; these are added
# to it at install/verify time.

# 0x1002 (AMD) device ids of the Raven-family APUs (Raven, Picasso), the
# only GPUs splash/'s vayu-kms early-KMS hook is built for.
hw_is_raven() {
  local d
  for d in /sys/bus/pci/devices/*; do
    [ "$(cat "$d/vendor" 2>/dev/null)" = 0x1002 ] || continue
    case $(cat "$d/device" 2>/dev/null) in 0x15d8|0x15dd) return 0 ;; esac
  done
  return 1
}

# Vendor ids of the display controllers (PCI class 0x03xxxx), one per line.
hw_gpu_vendors() {
  local d
  for d in /sys/bus/pci/devices/*; do
    case $(cat "$d/class" 2>/dev/null) in 0x03*) cat "$d/vendor" 2>/dev/null ;; esac
  done | sort -u
}

# Packages this machine's hardware needs, one per line.
#   CPU microcode     intel-ucode / amd-ucode (the mkinitcpio microcode hook
#                     packs whichever is installed)
#   Intel graphics    vulkan-intel (ANV) and intel-media-driver (VA-API,
#                     Broadwell and newer)
#   AMD graphics      vulkan-radeon (RADV; VA-API is part of mesa)
#   NVIDIA graphics   vulkan-nouveau (the open driver this setup runs on)
hw_packages() {
  case $(awk -F': ' '/^vendor_id/ { print $2; exit }' /proc/cpuinfo 2>/dev/null) in
    GenuineIntel) echo intel-ucode ;;
    AuthenticAMD) echo amd-ucode ;;
  esac
  local v
  for v in $(hw_gpu_vendors); do
    case $v in
      0x8086) echo vulkan-intel; echo intel-media-driver ;;
      0x1002) echo vulkan-radeon ;;
      0x10de) echo vulkan-nouveau ;;
    esac
  done
}
