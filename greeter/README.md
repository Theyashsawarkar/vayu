# greeter -- the tuigreet login screen (Mocha Rosé)

System files, not a stow package: `./apply.sh` installs them (needs sudo).

| File | Installed as |
|---|---|
| `config.toml` | `/etc/tuigreet/config.toml` -- layout, colours, sway command |
| `tuigreet-launch` | `/usr/local/bin/tuigreet-launch` -- greetd's greeter; puts `ace at <battery> NN%` in the title |
| `build-console-font.py` | builds `/usr/share/kbd/consolefonts/ter-v24n-ace.psf.gz` (Terminus 12x24 with rounded corners and icons) |
| `vtrgb`, `vt-palette.service` | `/etc/vtrgb` + unit -- Catppuccin Mocha, true black, on every tty |

`apply.sh` also sets `FONT=ter-v24n-ace` in `/etc/vconsole.conf`, rebuilds
the initramfs (the font is set there), and points `/etc/greetd/config.toml`
at the launcher. Reboot to see it.

Try a change without rebooting: `TUIGREET_CONFIG=./config.toml ./tuigreet-launch --mock`
in a terminal (kitty's own font and colours, so no rounded corners there).

The clock sits just above the box only at 160x45 cells (1920x1080 with a
12x24 font): `window_padding = 7` is tuned for that; change width, padding
or font and it needs retuning.

Rollback (from a tty2 login if needed):

```
sudo tee /etc/greetd/config.toml <<'T'
[terminal]
vt = 1

[default_session]
command = "tuigreet --time --remember --asterisks --cmd 'env XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=sway:wlroots:swayfx XDG_SESSION_DESKTOP=sway DESKTOP_SESSION=sway sway'"
user = "greeter"
T
sudo sed -i 's/^FONT=.*/FONT=default8x16/' /etc/vconsole.conf
sudo systemctl disable vt-palette.service && sudo mkinitcpio -P
```
