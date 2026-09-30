# greeter -- the tuigreet login screen (Mocha Rosé)

System files, not a stow package: `./apply.sh` installs them (needs sudo).

| File | Installed as |
|---|---|
| `config.toml` | `/etc/tuigreet/config.toml` -- layout, colours, sway command |
| `tuigreet-launch` | `/usr/local/bin/tuigreet-launch` -- greetd's greeter; puts `Ace · NN%` (plus `· charging`) in the title |
| `tuigreet-center-box.patch` | built into `/usr/local/bin/tuigreet-ace` -- tuigreet 0.11.1 with the box centred on the screen (stock lifts it by `window_padding`); the launcher falls back to stock tuigreet with padding 0 if it's missing |
| `build-console-font.py` | builds `/usr/share/kbd/consolefonts/ter-v24n-ace.psf.gz` (Terminus 12x24 with rounded corners) |
| `vtrgb`, `vt-palette.service` | `/etc/vtrgb` + unit -- Catppuccin Mocha, true black, on every tty |

`apply.sh` also sets `FONT=ter-v24n-ace` in `/etc/vconsole.conf`, rebuilds
the initramfs (the font is set there), and points `/etc/greetd/config.toml`
at the launcher. Reboot to see it.

Try a change without rebooting: `TUIGREET_CONFIG=./config.toml ./tuigreet-launch --mock`
in a terminal (kitty's own font and colours, so no rounded corners there).

The box (rows 18-26) is centred on the 160x45 screen (1920x1080 with a
12x24 font), and `window_padding = 16` puts the clock one row above it. The
padding is tuned for that size; a different font or resolution needs
retuning. Keep the clock text an even width (28) so it centres exactly over
the 44-wide box.

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
sudo rm -f /usr/local/bin/tuigreet-ace
```
