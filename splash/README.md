# splash/ -- the Vayu boot splash

Between the firmware logo and the login screen, Plymouth shows the Vayu
logo instead of kernel and systemd text: the letters write themselves, the
wind line sweeps out and curls, then a soft light keeps running along the
wind line until tuigreet takes over. Reboot and power-off show it too
(Plymouth's own shutdown units): `vayu-splash-hold.service` keeps the
machine up until the intro has finished even when shutdown is quicker, and
`vayu-splash-blank.shutdown` keeps the screen black from the logo to the
firmware.
Press Esc for the full log.

| File | What |
|---|---|
| `logo.svg` | the logo itself (hairline capitals, wind line), for use anywhere |
| `make-frames.py` | renders the animation into `theme/*.png` (needs `rsvg-convert`) |
| `theme/` | the Plymouth script theme, installed to `/usr/share/plymouth/themes/vayu/` |
| `plymouthd.conf` | selects the theme, no show delay; installed to `/etc/plymouth/` |
| `vayu-splash-hold.service` | on reboot/power-off, holds the final step until the intro has played (2.6 s from the splash appearing) |
| `vayu-splash-blank.shutdown` | `systemd-shutdown` hook: blanks the console (all colours black) just before the last shutdown step switches it back to text mode, so no text shows after the logo |
| `initcpio/`, `mkinitcpio-vayu-kms.conf` | the `vayu-kms` hook: early amdgpu with only this APU's firmware (Raven-family APUs only) |
| `apply.sh` | installs all of it (see below); `--check` is what `vayu-verify` runs |

`apply.sh` installs `plymouth`, the theme and `plymouthd.conf`, puts the
`plymouth` hook after `consolefont` (before `block`) in `/etc/mkinitcpio.conf`,
appends `quiet splash loglevel=3 rd.udev.log_level=3 plymouth.use-simpledrm` to
`/etc/kernel/cmdline`, installs the `vayu-kms` hook on Raven-family APUs, then
rebuilds the UKI (`mkinitcpio -P`).

## Why the boot is ordered this way

amdgpu costs ~3 s of CPU to load on this Ryzen 3 3250U, however it's loaded
(measured: `i915`, a third of its size, takes ~1 s compressed or not; the
time is the kernel's own module processing). Loaded from the root
filesystem it landed in the middle of userspace start-up: everything stalled
for 5-8 s, the greeter appeared at ~14 s, and amdgpu then replaced the
firmware framebuffer under it (console 160x50 -> 240x67 -> font applied ->
tuigreet re-laid out: the flicker).

So `vayu-kms` (`/etc/initcpio/install/vayu-kms`) loads `acpi_cpufreq` (CPU
boost) and then amdgpu as the initramfs's first job, before udev triggers
anything. It packs only the firmware matching `VAYU_AMDGPU_FIRMWARE` (~400 KB
of `raven*`/`picasso*`), not the stock `kms` hook's ~30 MB for every AMD GPU
(the 47 MB image that cost 5.8 s of loader time). Then `consolefont` sets the
font on the final display (160x45), Plymouth starts on amdgpu, and the
Acer logo stays up until the Vayu animation replaces it.

`plymouth.use-simpledrm` stays as a fallback: if amdgpu ever fails, Plymouth
still draws on the firmware framebuffer.

To change the logo or the timing, edit `make-frames.py`, run it, check the
frames, commit them, then run `apply.sh`.

## Rollback

```sh
sudo systemctl disable --now vayu-splash-hold.service; sudo rm /etc/systemd/system/vayu-splash-hold.service
sudo rm /usr/lib/systemd/system-shutdown/vayu-splash-blank.shutdown
sudo rm /etc/mkinitcpio.conf.d/vayu-kms.conf /etc/initcpio/install/vayu-kms /etc/initcpio/hooks/vayu-kms
sudo sed -i -E '/^HOOKS=/s/ plymouth\b//' /etc/mkinitcpio.conf
sudo sed -i -E 's/ (quiet|splash|loglevel=3|rd\.udev\.log_level=3|plymouth\.use-simpledrm)\b//g' /etc/kernel/cmdline
sudo mkinitcpio -P
```

If a boot ever seems stuck on the logo, press Esc to see the log. The splash
can't stop a boot by itself: if Plymouth or the theme fails, boot carries on
in text mode.
