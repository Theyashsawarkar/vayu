# Troubleshooting

Known problems and edge cases, by symptom: what you see, why it happens, and
what to do. Every fix here is something you can run as-is. For a full record
of how each one was found, follow the link to its `CHANGELOG.md` entry.

**Start here, whatever the problem:**

```sh
vayu-verify                        # does this machine still match the repo? lists anything that differs
vayu-logs                          # warnings and errors from every part of the desktop, this boot
vayu-logs --list                   # which tools logged, how much, how many warnings
vayu-logs vyom                     # one tool (vyom, nada, waybar, bar-events, claude-tmux...)
journalctl -b -1 -p 0..3 --no-pager  # errors from the previous boot (the one that went wrong)
```

Every tool logs to the journal under its own name, tracebacks included (see
`docs/ARCHITECTURE.md`, "Every long-running piece is a user unit"). A part
that's gone (no bar, no clipboard history): `systemctl --user status <name>`;
each restarts itself on a crash, with backoff.

Most "it stopped working after an update" cases are a `differs:` line in
`vayu-verify`: the repo changed but the root-owned part wasn't re-applied.
The update notification says which script to run. If you missed it:

```sh
~/dotfiles/system/apply.sh    # files under / (sysctl, systemd drop-ins, PAM, ...)
~/dotfiles/splash/apply.sh    # boot/shutdown splash
~/dotfiles/greeter/apply.sh   # login screen
~/dotfiles/install.sh         # everything, including new packages; safe to re-run
```

**Escape hatches worth knowing before you need them:**

| Keys | What it does |
|---|---|
| `Esc` on the Vayu logo | Shows the boot or shutdown log behind the splash. Press again to go back. |
| `Ctrl+Alt+F2` | A text login on tty2, when the login screen or desktop won't come up. `Ctrl+Alt+F1` goes back. |
| Hold `Alt+PrtSc`, press `S` `U` `B` | Kernel SysRq: sync disks, remount read-only, reboot. Works when nothing else responds. Use `O` instead of `B` to power off. |
| Hold the power button ~10 s | Last resort. Unlike SysRq, unwritten data is lost. |

SysRq needs `kernel.sysrq = 176` (`system/etc/sysctl.d/99-sysrq.conf`,
installed by `system/apply.sh`). Check with `sysctl kernel.sysrq`. Press the
letters about a second apart, holding `Alt+PrtSc` the whole time. On keyboards
where PrtSc needs `Fn`, hold `Fn` too.

## Wi-Fi: it drops for a moment, with iwlwifi errors in the journal

The Wi-Fi card's firmware crashes and the driver resets it, usually within a few
seconds: `journalctl -k -g "Device error - SW reset"` shows `iwlwifi` "HW error,
resetting". It happened 7 times in 36 hours on the machine this was checked on,
and came back each time. It's the kernel driver and Intel's firmware, not Vayu.
If it gets frequent, update `linux-firmware` and the kernel first.

## Audio: sound blips once and WirePlumber restarts

`coredumpctl list wireplumber` shows a crash in `libspa-bluez5.so` (PipeWire's
Bluetooth code, one crash in 36 hours when this was checked). systemd restarts it
in a second, so audio comes back alone. It's upstream: update `pipewire`.

## Shutdown: the logo stays up and the machine doesn't turn off

**Why:** a service is taking long to stop. systemd waits up to 90 s per
service (`DefaultTimeoutStopSec`), then kills it. If shutdown as a whole is
stuck, systemd forces the reboot/power-off after 30 min
(`JobTimeoutAction=reboot-force` on `reboot.target`). The logo hides the
countdown.

**What to do:**

1. Press `Esc`. A line like `A stop job is running for <service> (1min 2s / 1min 30s)` names the service.
2. Wait for it (at most 90 s per service), or use SysRq `S` `U` `B` (see above) to reboot now without losing written data.
3. After the next boot, see what held it up:

   ```sh
   journalctl -b -1 -e --no-pager | grep -E 'stop job|Timed out|Killing'
   ```

4. If the same service does it every time, cap its stop timeout (replace `NAME`):

   ```sh
   sudo systemctl edit NAME.service
   # add, between the comment lines:
   # [Service]
   # TimeoutStopSec=10s
   ```

The splash itself adds at most 2.6 s (`vayu-splash-hold.service`, so the
intro can finish) and can't hang: it's a `sleep 2.6`, and it's skipped when
Plymouth isn't running.

## Shutdown: the screen goes black but the machine stays on

**Why:** the last step of shutdown (unmounting, then the kernel switching
the hardware off) is stuck, usually in a driver or firmware. On this setup
that step is invisible on purpose: `vayu-splash-blank.shutdown` turns the
console black on black so no text shows after the logo. It also has no
automatic reset: `RebootWatchdogSec=0` (see the next section) stopped the
hardware watchdog from rebooting a machine stuck there after 10 min.

**What to do:**

1. Hold `Alt+PrtSc` and press `S`, `U`, then `O` (power off) or `B` (reboot), a second apart.
2. If that does nothing, hold the power button for ~10 s.
3. If it happens more than once, look at what the last step prints. Do this once, then restore:

   ```sh
   # 1. let the final text show: disable the blanking hook...
   sudo chmod -x /usr/lib/systemd/system-shutdown/vayu-splash-blank.shutdown
   # ...and drop quiet/loglevel from the kernel command line
   sudo sed -i -E 's/ (quiet|loglevel=3)\b//g' /etc/kernel/cmdline && sudo mkinitcpio -P
   # 2. reboot and read (or photograph) the screen at the end of shutdown
   # 3. restore both: apply.sh re-adds the options and re-enables the hook
   ~/dotfiles/splash/apply.sh
   ```

   Look for the last lines before it stops (often a driver name or
   `INFO: task ... blocked`).

## Shutdown: I want the automatic 10-minute reset back

For an unattended machine (no one to press SysRq), you may prefer the
watchdog over a clean screen. Remove the drop-in and re-execute systemd:

```sh
sudo rm /etc/systemd/system.conf.d/no-reboot-watchdog.conf
sudo systemctl daemon-reexec
systemctl show -p RebootWatchdogUSec   # 10min = watchdog armed again
```

The cost: the kernel line `watchdog: watchdog0: watchdog did not stop!`
shows after the shutdown logo again (next section). `system/apply.sh`
reinstalls the drop-in, and `vayu-verify` reports it as missing. To keep it
removed, also delete
`~/dotfiles/system/etc/systemd/system.conf.d/no-reboot-watchdog.conf` in
your copy of the repo.

## Shutdown: text appears after the shutdown logo

What should happen: reboot shows the logo, then black, then the firmware
logo. Power-off shows the logo, then the machine turns off. What the text
looks like tells you which part is missing:

| You see | Cause | Fix |
|---|---|---|
| One line starting with a timestamp, e.g. `[  272.268042] watchdog: watchdog0: watchdog did not stop!` | The hardware watchdog drop-in isn't installed. | `~/dotfiles/system/apply.sh`, then check `systemctl show -p RebootWatchdogUSec` says `0`. |
| A full screen of white text | The blanking hook isn't installed or isn't executable. | `~/dotfiles/splash/apply.sh`, then `ls -l /usr/lib/systemd/system-shutdown/` should list `vayu-splash-blank.shutdown` as executable. |
| Some other line in brackets | Another kernel message urgent enough to pass `loglevel=3`. | Find it with `journalctl -k -b -1 -p 0..3 --no-pager`. The very last lines of a shutdown often aren't in the journal (it stops recording just before), so if it isn't there, use step 3 under "Shutdown: the screen goes black but the machine stays on". |
| Boot/shutdown text instead of the logo at all | Plymouth isn't running. | See "Boot: text instead of the Vayu logo". |

Background: the changelog entries
[no text after the shutdown logo](../CHANGELOG.md#2026-10-04-no-text-after-the-shutdown-logo)
and
[no watchdog line after the shutdown logo](../CHANGELOG.md#2026-10-04-no-watchdog-line-after-the-shutdown-logo).

## Boot: the firmware logo stays up for ~15 s

Expected on AMD Raven-family laptops (the Acer this was built on), not a
hang. Loading the `amdgpu` driver costs ~6 s
of CPU however it's loaded, and that time comes before the Vayu logo can
appear. Measured and explained in `splash/README.md` ("Why the boot is
ordered this way"). Only building amdgpu into a custom kernel would remove
it.

## Boot: stuck on the Vayu logo

The light keeps running along the wind line until the login screen starts,
so a logo that keeps animating means the login screen hasn't started.

1. Press `Esc` to see the boot log. The last lines say what it's waiting for.
2. `Ctrl+Alt+F2`, log in, and check the login screen service:

   ```sh
   systemctl status greetd
   journalctl -b -u greetd --no-pager | tail -30
   ```

3. If the login screen itself is broken, the rollback in
   [`greeter/README.md`](https://github.com/Theyashsawarkar/vayu/blob/development/greeter/README.md)
   puts back stock tuigreet from that tty2 login.

The splash can't stop a boot by itself: if Plymouth or the theme fails, boot
carries on in text mode.

## Boot: text instead of the Vayu logo

```sh
~/dotfiles/splash/apply.sh --check   # lists anything missing
cat /proc/cmdline                    # needs: quiet splash loglevel=3 rd.udev.log_level=3 plymouth.use-simpledrm
```

`~/dotfiles/splash/apply.sh` fixes whatever `--check` lists and rebuilds the
UKI. On a machine without `/etc/kernel/cmdline` (not a UKI setup) it can't
edit the command line and says so: add those options in your boot loader
instead.

To remove the splash completely, follow "Rollback" in
[`splash/README.md`](https://github.com/Theyashsawarkar/vayu/blob/development/splash/README.md).

## Boot: a blank screen for a few seconds before the logo

The `vayu-kms` early-graphics hook is only installed on AMD Raven-family
APUs; on every other GPU `system/apply.sh` keeps the stock `kms` hook in
`/etc/mkinitcpio.conf` (and puts it back if an older version removed it),
so the driver loads from the initramfs. If you still see this, check
`grep ^HOOKS /etc/mkinitcpio.conf` lists `kms`, then run `system/apply.sh`
and reboot. Without it Plymouth draws on the firmware framebuffer
(`plymouth.use-simpledrm`) until the real driver loads, which shows as a
blank screen or one flicker.

## Install: mpd or ydotool failed on a fresh machine

Both were fixed in the installer (CHANGELOG 2026-10-16); re-run
`install.sh` to pick that up. mpd failed with "Failed to access ~/Music:
No such file or directory": its directories didn't exist yet, and
`mpd.service.d/prepare-dirs.conf` now creates the ones `mpd.conf` names.
ydotool failed with "failed to open uinput device: Permission denied":
the `input` group and ydotool's udev rule only take effect after a
re-login/reboot, so the installer now grants your user an ACL on
`/dev/uinput` for the current boot. If either still fails:
`systemctl --user status mpd ydotool` and `getfacl /dev/uinput`.

## Git: a commit or push is refused with "secret-scan"

**What you see:** `git commit` or `git push` stops with red `secret-scan:`
lines: gitleaks found a secret (shown redacted), a file is a secret by its
kind (`.env`, a key, a keystore), or a line holds one of your private strings.
Nothing was committed or pushed.

**Why:** every repo's hooks (`~/.config/git/hooks`, `core.hooksPath`) run
`secret-scan` first, so no secret reaches GitHub (CLAUDE.md, "Secrets").

**What to do:**

- A real secret: take it out (an env var, a file outside the repo; add the
  file to `.gitignore`), then commit again. If it's already in a commit,
  `git reset --soft HEAD~1`, fix, commit again.
- A false alarm from gitleaks: put `gitleaks:allow` in a comment on that
  line, or its fingerprint (`gitleaks git --redact -v`) in the repo's
  `.gitleaksignore`, with a line saying why.
- `gitleaks isn't installed`: `sudo pacman -S gitleaks`.
- A repo using husky (its own `core.hooksPath`) doesn't get this scan: its
  own hooks run instead.
- Your private strings: `~/.config/git/private-patterns`, one extended
  regex per line; it never goes into a repo.

## Hardware: a different laptop than the one this was built on

Hardware-specific parts are detected, not hardcoded:
`packages/hardware.sh` picks microcode (intel-ucode/amd-ucode) and GPU
drivers (vulkan-intel + intel-media-driver, vulkan-radeon, vulkan-nouveau)
from `/proc/cpuinfo` and the PCI display controllers; the lid device
(`/proc/acpi/button/lid/*`), AC adapter (power_supply `type=Mains`),
battery and backlight are found at runtime. To see what this machine gets:
`source ~/dotfiles/packages/hardware.sh; hw_packages`. Still tied to the
original hardware: hibernate stays masked (it broke amdgpu resume there),
and the greeter layout assumes a 1920x1080 panel (160x45 console).

## Hotspot: devices join but nothing loads

The hotspot (`vayu-hotspot on`, the Wi-Fi menu, or the teal capsule) shares
this laptop's internet. Devices that connect but can't open anything are
almost always being dropped by the firewall: Docker and ufw set the FORWARD
chain to DROP, and the hook that lets hotspot traffic through isn't
installed. Install it and restart the hotspot:

```sh
~/dotfiles/system/apply.sh        # installs /etc/NetworkManager/dispatcher.d/50-vayu-hotspot
vayu-hotspot off && vayu-hotspot on
sudo iptables -S FORWARD | grep vayu-hotspot   # two ACCEPT rules while it's on
```

Also check `vayu-hotspot status` shows an **internet** source: the hotspot
shares a wired connection or a USB-tethered phone, not Wi-Fi (next
section). See the 2026-10-19 hotspot entry in `CHANGELOG.md`.

## Hotspot: my Wi-Fi disconnected when I started it

By design. NetworkManager can't keep this Wi-Fi card connected to a
network while it hosts one (most laptop cards can't, or only on the same
channel), so the hotspot takes the Wi-Fi card over and shares the wired
connection instead. `vayu-hotspot on` warns before it drops Wi-Fi.
`vayu-hotspot off` gives the card back; NetworkManager then reconnects to
your saved network by itself.

## Hotspot: my phone doesn't see it, or it won't start

- **Not in the phone's list:** the hotspot uses channel 6 (2.4 GHz), which
  every country allows. If you set another one, go back to it:
  `vayu-hotspot on --channel 6`.
- **"couldn't start it on 5 GHz":** many cards' firmware refuses to host on
  5 GHz until it has seen a 5 GHz network nearby. Use `--band bg`.
- **"can't be an access point":** this laptop's Wi-Fi card doesn't support
  hosting at all (`iw list` has no `AP` under "Supported interface modes").
  A USB Wi-Fi adapter that does works: `vayu-hotspot on --device <its name>`.
- **"needs dnsmasq":** `sudo pacman -S dnsmasq` (`install.sh` installs it
  on new machines).

## Panels: a key (Super+D, Super+Shift+W...) or a bar click opens nothing

Every launcher and panel is a [Vyom](https://github.com/Theyashsawarkar/vyom)
tool, each its own repo. See what Vyom has loaded and why anything is
skipped:

```sh
vyom list                                  # every tool: ok, or what it needs
tail -20 ~/.local/state/vyom/daemon.log    # errors from the panels
```

- **`vyom: command not found`, or a tool missing from the list:** a machine
  set up before Vyom (or before a tool was added) doesn't have it yet.
  `~/dotfiles/install.sh` (safe to re-run) clones Vyom and every tool in
  `VYOM_TOOLS` and updates the ones already there.
- **"needs X":** install X (`vyom list` names it), then `vyom reload`.
- **Nothing at all, even `vyom dvara` in a terminal:** Vyom needs
  `gtk4-layer-shell` and `python-gobject` (install.sh installs both).
  Restart it with `vyom quit; vyom daemon`.
- **The panel shows but looks like a flat box:** SwayFX's blur behind it
  comes from `layer_effects "vyom"` in sway's config; reload sway.

## Notifications: none show, or they look like the old mako ones

Notifications are akashvani's (inside Vyom; it replaced mako on 2026-11-17).
Only one program can serve notifications, so if mako (or dunst) is running it
holds the name and akashvani waits behind it: you see mako's popups, or none.

```sh
akashvani doctor                          # who serves notifications, and what's missing
systemctl --user stop mako.service        # mako is still running: stop it, akashvani takes over at once
akashvani status                          # on screen, held, history, modes
akashvani mode -s normal                  # popups held? do not disturb was on (Super+Ctrl+n does the same)
vayu-logs vyom                            # a traceback from the server or the popups
```

No popups but they're in `Super+Shift+n`: do not disturb is on (the bell in
the bar is the sleeping one), or a rule in `~/.config/vyom/config.toml`
(`[[plugin.akashvani.rules]]`) hides them. A notification sent while Vyom
restarts (a few seconds) waits for it: D-Bus starts Vyom through
`~/.local/share/dbus-1/services/org.freedesktop.Notifications.service`.
To go back to mako for a while: `systemctl --user start mako.service` (if mako
is still installed); akashvani waits behind it. See CHANGELOG.md, 2026-11-17.

## Lock: the screen locks again a minute after unlocking

Fixed on 2026-10-24 (see `CHANGELOG.md`). It happened after the laptop woke
and went back to sleep several times with the lid shut: the lock-on-sleep
hook waited for each lock to be unlocked, so the locks queued up and came
back one after another, one per sleep. Both idle configs now start swaylock
with `-f`, so it can't queue. If an old machine still does it, pull, then
restart the two services (clears any queued locks):

```sh
grep -n 'vayu-lock' ~/.config/sway/idle/config ~/.config/sway/idle/lock-on-sleep   # both should end in -f
systemctl --user restart swayidle.service swaylock-on-sleep.service
```

## Login: the desktop doesn't start after logging in

The screen returns to the login prompt or goes black. Sway's own log goes to
the journal (not the screen):

```sh
journalctl -b -t sway --no-pager | tail -40
```

Run it from a `Ctrl+Alt+F2` login. A config error shows with a line number;
`sway --validate` checks the config without starting it.

## Login: wrong colours or font on the login screen

The red box border or the rounded console font missing means
`vt-palette.service` or the console font isn't in place:

```sh
~/dotfiles/greeter/apply.sh
systemctl status vt-palette.service
```

## Suspend: the screen goes black on the lock screen after opening the lid

**Known, unresolved, rare.** Seen once: after a quick lid close/open, the
lock screen showed, then went black a few seconds later while typing the
password, and came back on its own. Nothing was logged.

**What to do:** wait a few seconds. If it doesn't come back, use SysRq
`S` `U` `B` rather than the power button. Then save what was logged and open
an issue:

```sh
journalctl -b -1 --since "-10 min" --no-pager > ~/lid-black-screen.log
```

Details: [Lid-close, suspend vs hibernate](ARCHITECTURE.md#lid-close-suspend-vs-hibernate-a-real-hibernateamdgpu-resume-crash)
in `docs/ARCHITECTURE.md`.

## Suspend: the laptop powered off with the lid closed

By design: after 30 min continuously closed, the laptop powers off instead
of staying suspended. Hibernate is removed on purpose (it corrupted the
amdgpu firmware reload). Change the delay, or test it safely, in
`/etc/lid-timeout-poweroff.conf` (repo copy:
`system/etc/lid-timeout-poweroff.conf`):

```sh
TIMEOUT_SECONDS=1800   # seconds the lid must stay closed
DRY_RUN=1              # notify instead of powering off (testing)
```

## Install: a step failed

`install.sh` doesn't stop at a failing step. The summary at the end prints a
`fix:` line under each one. Then:

```sh
grep -n 'command failed' ~/.local/state/vayu/install-logs/latest.log   # the exact failing command
less +G ~/.local/state/vayu/install-logs/latest.log                     # diagnostics are at the end
```

Fix the cause and run `install.sh` again: it skips what's already done.
Fallbacks keep the desktop usable: stock `sway` if `swayfx` won't build,
`yay-bin` if `yay` won't, stock `tuigreet` if the patched login screen
won't. The full list of what install needs first is in the
[README](https://github.com/Theyashsawarkar/vayu#readme).

## tmux: a row with Hindi or Marathi has stray characters or broken borders

kitty and tmux count some letters of Indian scripts differently: kitty puts a whole
syllable (का, स्क) in one cell, tmux gave its vowel sign and each joined consonant a cell
of their own. On a row holding such text, everything after it was drawn a few columns
further left than the program planned, leaving stray characters at the end of the row.

- **Vowel signs**: `tmux.conf` sets `codepoint-widths` so every spacing vowel sign takes
  no cell, as in kitty. Check it's loaded: `tmux show -s codepoint-widths`. A tmux older
  than 3.5 has no such option.
- **Joined consonants** (स्क, क्ष): no tmux setting fixes these. narada adds an invisible
  ZWNJ after the halant in what it draws, so both count the same (the consonants show
  joined by a halant, not as one shape). Other tools can still be a column off on such
  words.
- Another terminal than kitty may count differently again; the setting is safe to remove
  there.

## tmux: Esc doesn't close the session picker or the key search any more

The tmux pickers (`Ctrl+a s`, `Ctrl+a ?`) have vim modes now: they open typing
(INSERT, shown in the box's label), the first `Esc` goes to NORMAL, where `j`/`k` move
and `q` closes, and the second `Esc` closes. So closing takes `Esc Esc` (or `Esc q`).
In NORMAL, letters are commands and typing does nothing: press `i`, `a` or `/` to
type again.

## tmux: `Ctrl+a Space` opens a menu instead of changing the layout

`Ctrl+a Space` is the launcher (every tool by group). The layouts are still on
`Ctrl+a Alt+1` .. `Alt+7` (even horizontal, even vertical, main horizontal, main
vertical, tiled...). If the launcher's menu doesn't appear, the client may still be in
the launcher's key table: press `Esc`; and check `whichkey.sh` in `vayu-logs whichkey.sh`.

## Phone: Super+o says "ekatva is off", or the phone doesn't connect after a reboot

ekatva is off by default and stays the way you left it: turn it on with the
"Phone link" tile in quick settings (`Super+q`), or `ekatva-toggle.sh on`. While
it's on, a green phone capsule is on the bar (right click turns it off). The
switch is the file `~/.local/state/ekatva-switch/enabled` (there = on);
`sway-session.sh` starts ekatva at login only when it exists.

## Boot: I need the boot menu (another kernel, the firmware setup)

The menu no longer waits 3 s on every boot (`timeout 0`). Hold Space while the
machine starts and it shows. To have it every time again, set `timeout 3` in
`/boot/loader/loader.conf`, and drop the `loader.conf` block in `system/apply.sh`,
or the next run sets it back.

## Video: a site won't play a video, or plays it in low quality

Zen and Firefox have AV1 turned off on GPUs that can't decode it
(`browser-perf-prefs`), so sites send VP9 or H.264, which the GPU decodes. A site
that only offers AV1 (rare) then can't play. To allow it, set `media.av1.enabled`
to true in `about:config` and delete that line from the marked block in the
profile's `user.js` (`browser-perf-prefs` writes it back on the next login: remove
the AV1 lines from the script too).

## Docker: containers are slow while I work

On purpose: containers run in `containers.slice` with a third of the desktop's
CPU and disk weight, so they slow down only while you use the machine, and get
all of it when you don't. For a benchmark, run it with the desktop idle, or
remove `cgroup-parent` from `/etc/docker/daemon.json` (and `system/etc/docker/`)
and restart Docker.

## Performance: a background job (mail sync, an update check) runs slowly

narada, vesha, vishvakarma, ekatva, update-check, tmux-autosave and
the wallpaper fetcher run in systemd's `background.slice` (CPU weight 30, the
apps and panels you use have 100), so they wait while something you use needs
the CPU: a compile, a browser loading a page. That's on purpose: it is what keeps
the launcher and windows quick on a 2-core laptop. Idle, they run at full speed.
To give one its normal share back, delete its
`~/.config/systemd/user/<unit>.service.d/background.conf` (in the repo:
`systemd/.config/systemd/user/`), then `systemctl --user daemon-reload` and
restart it. See which slice a unit is in with
`systemctl --user show -p Slice <unit>`.

## Performance: the bar's mail or WhatsApp count is a few seconds late

bar-events asks narada for its unread counts at most every 3 seconds (it
used to every second or so while WhatsApp synced, 8% of a core at idle), so a
count can lag that long behind reading a message. It always catches up with
the last change.

## Panels: the launcher was slow the first time after a boot

Vyom (0.7.4 and later) draws the launcher once off screen when it starts, so the
first Super+d is as quick as the others. If you press it in the first second or
two after login it can still wait for that to finish. `journalctl --user -u vyom`
logs "first frame in N ms" for any opening over 150 ms. `[vyom] warm_up = false`
in `~/.config/vyom/config.toml` turns the warm-up off.

## A Vyom tool shows less than it should, or the bar's counts are wrong

The keybinding search shows only Sway's keys, or a capsule disagrees with the
tool. A long-running user service can be out of date, or missing `~/.local/bin`
from its PATH (a new login picks up `environment.d`):

```sh
systemctl --user show-environment | grep ^PATH       # should start with ~/.local/bin
systemctl --user restart vyom.service bar-events.service
```

## AI tools: the approval window closed but the agent is still waiting

Normal since dvarapala 1.5.0: the window goes when you answer and the agent
waits for the commands to finish (30 minutes at most each). A failure shows
up in what the agent reports, not on screen. If you hid a request with
`Ctrl+H` without answering, the agent waits until it expires as denied, up to
10 minutes; a hidden window can't be brought back, so use `Esc` to say no.

```sh
systemctl --user list-units 'dvarapala-*'   # a run or a hidden request still going
```

## AI tools: the approval window doesn't appear

The agent got `"status": "error"` back, or it's waiting and nothing shows.

```sh
~/.local/share/dvarapala/install.sh --check         # installed? (run it without --check to install)
journalctl --user -u 'dvarapala-*' -n 30 --no-pager   # the window's own errors
echo "$WAYLAND_DISPLAY"                           # the agent must run inside your desktop session
```

The window needs your Wayland session: an agent running over SSH or in a
container without `XDG_RUNTIME_DIR` can't open it (the error says "no
Wayland session found"). If notifications are in Do Not Disturb you won't
get the "Root access requested" popup, but the window still opens on the
current workspace.

## AI tools: a command hung or failed only under dvarapala

Commands run as root with no input and no terminal, from `/`, with root's
environment. So:

- anything that asks a question waits until its 30-minute limit: use
  `--noconfirm`, `-y`, `-f`;
- `~` means `/root`, not your home: write `/home/<user>/...`;
- relative paths are relative to `/`.

The full output is in the result the agent got, and every run is logged:
`sudo tail /var/log/dvarapala.log | jq .`.

## AI tools: I approved by mistake, or want to see what ran

Everything that ran as root is in `/var/log/dvarapala.log` (one JSON line
per command, with its exit code), and every request, including denied ones,
in `~/.local/state/dvarapala/requests.jsonl`. There's no undo: reverse it
by hand (e.g. `pacman -R`, `systemctl disable`). To stop agents using the
tool: `~/.local/share/dvarapala/install.sh --uninstall`. (dvarapala was called
vayu-elevate before 2026-10-21; that name is now a link to it.)

## tmux bar: the Claude usage capsule is missing

The capsule (`  ritesh 6%`) shows only with two accounts or more and
known usage. See what vesha would show, and what tmux has:

```
vesha waybar --once
tmux show -gv @claude_limit
```

If vesha prints a line but tmux has nothing, tmux missed it (it started
after bar-events.py, or its server restarted): `bar-events.py --tmux-claude`
sets it now, and tmux.conf runs that on every load. An empty `text` or class
`unknown`/`error` means vesha couldn't read the usage: `vesha doctor`, and
`~/.local/state/vesha/watch.log` for the watcher.

## tmux bar: the Claude usage capsule is a few minutes late after a reset

bar-events runs `vesha waybar --once` when vesha's accounts, usage cache or
config change (the files `vesha waybar --sources` names), instead of keeping
`vesha waybar` running to look once a minute. A switch shows at once and a
usage change within a minute, but a usage window *resetting* changes the
number without changing a file: it shows when the watcher next writes the
usage cache (every few minutes; `vesha watch` must be running, `vesha
doctor`), or at the next Claude reply. To refresh it now:
`bar-events.py --tmux-claude`. bar-events says in its log (`vayu-logs
bar-events`) when it falls back to the old stream (a vesha before v0.7.0).

## Bar: the sound icon (or bell, lamp, phone, Docker) doesn't change

These capsules are written by bar-events: it follows the sound server
(`pactl subscribe`), notifications, the units and Docker, writes each line
to `$XDG_RUNTIME_DIR/vayu/bar/<name>.json` and signals waybar, which only
`cat`s the file. If one is stuck, bar-events isn't running or lost what it
follows:

```
systemctl --user status bar-events.service
vayu-logs bar-events            # "pactl subscribe exited ..." when PipeWire restarted
ls $XDG_RUNTIME_DIR/vayu/bar/    # the lines it wrote
~/.local/bin/bar-volume --once  # what the sound capsule should show
```

bar-events follows the sound server again by itself (2 s after it goes,
then longer, up to a minute, while it stays gone);
`systemctl --user restart bar-events.service` forces it. Stopping it removes
the files, and waybar runs each capsule's script itself again (the sound
capsule then stays as it was until waybar restarts).

## tmux bar: the PR capsule shows the wrong account's PRs, or an old count

The capsule (`  N` your open PRs, `󰊤 N` waiting for your review) counts
the account sangam shows: the one picked there with `u`, or all accounts
when "all" is picked; with nothing picked, gh's active one (`gh auth
switch`). See whose numbers it shows, and what it would count now:

```
tmux show -gv @gh_account
gh-review-count --account
```

It recounts as soon as the account changes or sangam changes a PR, 30 s
after that, and every 2 minutes. A PR merged or closed on github.com shows
up within 2 minutes; press `R` in sangam (or open it) to recount at once.
If it never changes, bar-events isn't running or can't reach GitHub:
`systemctl --user status bar-events`, `vayu-logs gh-review-count`.

## AI tools: sangam's approval popup doesn't appear

A comment, review or merge an agent asks for through `sangam mcp` opens a
popup on the agent's tmux pane, or the tmux client you used last. With no
tmux client attached, a desktop notification asks instead; with neither,
sangam refuses the write and tells the agent so. Unanswered for 10
minutes, it counts as declined. Check the server is registered:
`claude mcp list` should show `sangam: sangam mcp`.

## AI tools: an agent doesn't have a Vayu tool or skill

vishvakarma gives every agent Vayu's MCP servers and skills, at login and on
every kosha change. Ask it what's missing:

```
vishvakarma doctor
```

- **"out of date"**: run `vishvakarma sync`, then restart the agent: a running
  session keeps the tools it started with.
- **"`<tool>` isn't installed"**: vishvakarma only registers tools whose
  command exists; install it (`kosha install <tool>`).
- **"skip server X: you have your own"** or **"is your own folder"**: a
  server or skill of the same name was already set up by hand, and yours
  wins. Remove yours (`claude mcp remove --scope user X`, or the folder)
  and sync to get Vayu's.
- **An agent isn't listed at all**: vishvakarma knows Claude Code, Codex,
  opencode and Gemini CLI, found by their command or config folder; any
  other agent can read the skills in `~/.agents/skills`.
- The login sync's output: `journalctl --user -u vishvakarma`.

## Fonts: a browser's tabs, menus or address bar are too big (or too small)

Chrome, Zen (Firefox) and other GTK apps take their interface font from GTK's
`font-name` setting in dconf, not from the web pages' sizes. If another tool
(nwg-look, a GNOME settings app) changes it, every browser's chrome looks out of
proportion with the page. Check and reset it:

```sh
gsettings get org.gnome.desktop.interface font-name   # Vayu's: 'Adwaita Sans 11'
gsettings set org.gnome.desktop.interface font-name 'Adwaita Sans 11'
```

Then restart the browser. Page text is a separate setting: Chrome's
`chrome://settings/fonts`, Zen's Settings > Fonts, and each site's zoom (`Ctrl+0`
resets it).

## Keys: I don't know (or forgot) a keybinding

`Super+Shift+/` searches every keybinding on the system (sway, tmux, kitty,
zed, nāda, the Vyom panels, popups, and the SysRq combos above). In tmux, `prefix ?` lists
tmux's keys and runs the one you pick. Search action then object:
"kill window", "reboot hung".

## Reporting a problem

Include the output of these, from the boot where it happened if you can:

```sh
vayu-verify
git -C ~/dotfiles describe --tags --always   # which version you're on
journalctl -b -1 -p 0..4 --no-pager          # previous boot; -b for this one
```

Open an issue at
[github.com/Theyashsawarkar/vayu/issues](https://github.com/Theyashsawarkar/vayu/issues).

## Recording: the laptop gets hot, no sound, or no mic

Super+r / Super+Shift+r record with the GPU's encoder (VA-API) when the
GPU can, otherwise with the CPU (libx264), which is slower and heats the
laptop. The start notification says which ("GPU encoding" / "CPU
encoding"). CPU on a machine with an Intel/AMD GPU usually means its VA-API
driver is missing: `intel-media-driver` (Broadwell and newer) or
`libva-intel-driver` (older Intel), `libva-mesa-driver` (AMD).

Sound is the system's output (what you hear), not the microphone. "no
sound" means `pactl get-default-sink` found no sound server. Details of
the last attempts: `vayu-logs wf-recorder`.

## Tools: updating or reinstalling Vayu's tools (kosha)

Vayu's own tools (the Vyom panels and their tools, nāda, drishya, dvarapala,
pramana, sangam, narada, pattan, nauka...) are installed by
[kosha](https://theyashsawarkar.github.io/kosha/). At login a notification
offers "Update now" when any has a new release.

```sh
kosha fetch                # what's new on GitHub vs yours (changes nothing)
kosha list --installed     # versions, and what has an update
kosha update               # update everything (prints what changed)
kosha doctor               # missing programs, broken links, local changes
kosha install nada@0.1.0   # go back to (and pin) an older release; kosha unpin nada later
```

"has local changes" means a tool's folder was edited: commit or stash the
change there, or `kosha update --force` (stashes it). dvarapala's and
pramana's updates run their installers, which ask for your password: run
them in a terminal.

## Neovim: a pane I'm not in shows an old statusline or old signs

Since 2026-11-27 Neovim stops its plugins' polling timers (lualine, noice,
which-key, snacks' statuscolumn, lazy.nvim's config check) 2 s after it
loses focus, and starts them again when it gets focus back or you press a
key (`nvim/.config/nvim/lua/quiet.lua`). Idle, an unfocused Neovim went
from ~117 wakeups and ~5 ms of CPU a second to none. The cost: a Neovim in
a pane you can see but aren't in keeps its last statusline, clock and
signs until you go back to it (they catch up within a few milliseconds).
It relies on tmux's `focus-events` (on in tmux.conf); without them nothing
is paused. To turn it off, remove the `require("quiet").setup()` line at
the end of `lua/config/autocmds.lua`.

## Bar: the hotspot capsule still counts a device that left

The hotspot capsule changes only on events since 2026-11-27 (it also ran
every 30 s): NetworkManager's, and `iw event` when a device joins or
leaves. A device that goes away without saying so (out of range, battery
died) is dropped by the access point after a few idle minutes, and the
capsule follows then. Clicking it (the hotspot panel) shows the live list.
