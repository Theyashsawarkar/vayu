# splash/ -- the Vayu boot splash

Between the firmware logo and the login screen, Plymouth shows the Vayu
logo instead of kernel and systemd text: the letters write themselves, the
wind line sweeps out and curls, then a soft light keeps running along the
wind line until tuigreet takes over. Press Esc during boot for the full log.

| File | What |
|---|---|
| `logo.svg` | the logo itself (hairline capitals, wind line), for use anywhere |
| `make-frames.py` | renders the animation into `theme/*.png` (needs `rsvg-convert`) |
| `theme/` | the Plymouth script theme, installed to `/usr/share/plymouth/themes/vayu/` |
| `plymouthd.conf` | selects the theme, no show delay; installed to `/etc/plymouth/` |
| `apply.sh` | installs all of it (see below); `--check` is what `vayu-verify` runs |

`apply.sh` installs `plymouth`, the theme and `plymouthd.conf`, adds the
`plymouth` hook after `udev` in `/etc/mkinitcpio.conf`, appends `quiet splash
loglevel=3 rd.udev.log_level=3 plymouth.use-simpledrm` to `/etc/kernel/cmdline`,
then rebuilds the UKI (`mkinitcpio -P`).

`plymouth.use-simpledrm` matters here: there is no `kms` hook (see
`system/apply.sh`), so amdgpu only loads from the root filesystem a few
seconds in. Plymouth draws on the firmware framebuffer (simpledrm) until
then and moves to amdgpu when it appears.

To change the logo or the timing, edit `make-frames.py`, run it, check the
frames, commit them, then run `apply.sh`.

## Rollback

```sh
sudo sed -i -E '/^HOOKS=/s/ plymouth\b//' /etc/mkinitcpio.conf
sudo sed -i -E 's/ (quiet|splash|loglevel=3|rd\.udev\.log_level=3|plymouth\.use-simpledrm)\b//g' /etc/kernel/cmdline
sudo mkinitcpio -P
```

If a boot ever seems stuck on the logo, press Esc to see the log. The splash
can't stop a boot by itself: if Plymouth or the theme fails, boot carries on
in text mode.
