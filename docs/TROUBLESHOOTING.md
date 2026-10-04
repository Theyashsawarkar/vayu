# Troubleshooting

Known problems and edge cases, by symptom: what you see, why it happens, and
what to do. Every fix here is something you can run as-is. For a full record
of how each one was found, follow the link to its `CHANGELOG.md` entry.

**Start here, whatever the problem:**

```sh
vayu-verify                        # does this machine still match the repo? lists anything that differs
journalctl -b -1 -p 0..3 --no-pager  # errors from the previous boot (the one that went wrong)
journalctl -b -p 0..3 --no-pager     # errors from this boot
```

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

Expected on this laptop, not a hang. Loading the `amdgpu` driver costs ~6 s
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

## Boot: a blank screen for a few seconds before the logo (not this laptop)

The `vayu-kms` early-graphics hook is only installed on AMD Raven-family
APUs (the laptop this is built on). Elsewhere Plymouth draws on the firmware
framebuffer (`plymouth.use-simpledrm`) until the real GPU driver loads, so
the screen can stay blank or flicker once. Harmless; adding your GPU's
driver to the initramfs (the stock `kms` hook) removes it at the cost of a
bigger, slower-loading image.

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

## AI tools: the approval window doesn't appear

The agent got `"status": "error"` back, or it's waiting and nothing shows.

```sh
~/dotfiles/ai/apply.sh --check                    # installed? (run it without --check to install)
journalctl --user -u 'vayu-elevate-*' -n 30 --no-pager   # the window's own errors
echo "$WAYLAND_DISPLAY"                           # the agent must run inside your desktop session
```

The window needs your Wayland session: an agent running over SSH or in a
container without `XDG_RUNTIME_DIR` can't open it (the error says "no
Wayland session found"). If notifications are in Do Not Disturb you won't
get the "Root access requested" popup, but the window still opens on the
current workspace.

## AI tools: a command hung or failed only under vayu-elevate

Commands run as root with no input and no terminal, from `/`, with root's
environment. So:

- anything that asks a question waits until its 30-minute limit: use
  `--noconfirm`, `-y`, `-f`;
- `~` means `/root`, not your home: write `/home/<user>/...`;
- relative paths are relative to `/`.

The full output is in the result the agent got, and every run is logged:
`sudo tail /var/log/vayu-elevate.log | jq .`.

## AI tools: I approved by mistake, or want to see what ran

Everything that ran as root is in `/var/log/vayu-elevate.log` (one JSON line
per command, with its exit code), and every request, including denied ones,
in `~/.local/state/vayu-elevate/requests.jsonl`. There's no undo: reverse it
by hand (e.g. `pacman -R`, `systemctl disable`). To stop agents using the
tool: `sudo rm -rf /usr/local/bin/vayu-elevate /usr/local/lib/vayu-elevate`.

## Keys: I don't know (or forgot) a keybinding

`Super+Shift+/` searches every keybinding on the system (sway, tmux, kitty,
zed, rmpc, popups, and the SysRq combos above). In tmux, `prefix ?` lists
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
