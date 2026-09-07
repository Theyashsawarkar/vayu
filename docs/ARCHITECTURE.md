# How this repo works

## The model

One repo, managed with [GNU Stow](https://www.gnu.org/software/stow/). Every top-level
directory except `packages/` and `docs/` is a **stow package**: its internal path
structure mirrors where it belongs under `$HOME`, and `stow package` symlinks it into
place. `tmux/.config/tmux/tmux.conf` becomes `~/.config/tmux/tmux.conf -> ../dotfiles/tmux/.config/tmux/tmux.conf`.
Nothing here is copied onto the live system — it's all symlinks, so editing
`~/.config/tmux/tmux.conf` and editing the file in this repo are the same action.

`packages/pacman.txt` and `packages/aur.txt` are the exception: plain package-name
manifests, not something stow ever touches.

As of v1.0.0, this repo follows a real `main`/`develop` branch and release
process -- see `docs/VERSIONING.md` for the full model. Day-to-day work
happens on `develop`; `main` only ever moves via a tested, tagged release.

## Package map

<div class="pkg-grid" markdown="1">

<div class="pkg-card" markdown="1">
<h4><code>sway</code> <span class="pkg-path"><code>~/.config/sway/</code></span></h4>
<p>Window manager, keybindings, lock/idle config</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>waybar</code> <span class="pkg-path"><code>~/.config/waybar/</code></span></h4>
<p>Top status bar</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>wofi</code> <span class="pkg-path"><code>~/.config/wofi/</code></span></h4>
<p>App launcher / dmenu-style prompts</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>nwg-bar</code> <span class="pkg-path"><code>~/.config/nwg-bar/</code></span></h4>
<p>Power menu (Lock/Logout/Suspend/Reboot/Shutdown) -- absolute paths only, no shell involved anywhere in its invocation chain.</p>
<details markdown="1"><summary>Full details</summary>

One button-grid popup menu now (`bar.json`: the power button, Lock/Logout/Suspend/Reboot/Shutdown) -- `docker.json` used to live here too, replaced by `docker-picker.py` for the same reason the Wi-Fi/Bluetooth pickers exist (see the changelog): asked for the docker module to actually show which containers are running, not a static two-button menu, which is exactly the kind of dynamic content nwg-bar cannot do. See the changelog for why this isn't wofi -- its `--dmenu` mode hit several real, separately-confirmed limits for a *button-grid* popup specifically (no CSS cursor support, `--columns` capped at 2, `--hide-search` breaks rendering, `close_on_focus_loss` fights `focus_follows_mouse`) -- though wofi's `--dmenu` mode works fine for a plain scrolling list, see `networkmanager-dmenu`/`wifi-picker.py`/`bluetooth-picker.py` below. **Important, and it bit twice**: nothing in the `nwg-bar` invocation chain goes through a shell -- neither its own `exec` commands (`exec.Command()` directly, confirmed by reading the source) nor its `-t`/`-s` flag values (confirmed by testing `env nwg-bar -t '~/...'` directly -- it doesn't even detect a non-absolute path the way it does for the `icon` field, it just concatenates onto its default config dir and fails outright). **Never use `~` anywhere in an `nwg-bar` invocation or its JSON `exec` fields — always the absolute path.** Icons: either an absolute file path, or a name from the system icon theme (`createPixbuf()` falls back to `gtk.IconThemeGetDefault().LoadIcon()`) -- verify a given icon name actually exists in the installed theme (`find /usr/share/icons/<theme> -iname '<name>.svg'`) before using it, the same discipline as verifying Nerd Font codepoints elsewhere in this repo. **`volume.json`, `wifi.json`, and `bluetooth.json` used to exist here too, all three removed** -- `nwg-bar` only renders static buttons from a fixed JSON file (confirmed reading its Go source: no scale/slider/dynamic-list widget type exists in its schema at all, and its `launch()` fires a 150ms auto-`gtk.MainQuit()` after *every* click), so anything needing a live scan (Wi-Fi/Bluetooth devices) or continuous adjustment (volume) is architecturally impossible here -- looked like broken commands but was really just the wrong tool for the job. Volume/brightness, Wi-Fi, and Bluetooth are all handled below instead.

</details>
</div>

<div class="pkg-card" markdown="1">
<h4><code>docker-picker.py</code> <span class="pkg-path"><code>~/.local/bin/docker-picker.py</code> (<code>scripts/</code> package)</span></h4>
<p>Docker picker for waybar's docker module -- per-container info, Restart/Stop actions, verified against real containers.</p>
<details markdown="1"><summary>Full details</summary>

Docker picker for waybar's `docker` module -- replaced `nwg-bar`'s static docker.json (Stats / Stop All, no visibility into what's actually running, the same architectural gap the Wi-Fi/Bluetooth pickers exist for). Same wofi `--dmenu` approach as the other two pickers, self-contained on the `docker` CLI directly (no upstream tool to wrap here). Per running container: one Sky info row (name, image, status, ports -- view-only, selecting it just re-shows the same info via `notify-send`, never destructive) plus two action rows right after it, Peach "Restart" and Red "Stop" -- deliberately two different colors for these rather than reusing one "command" color the way the other pickers do, since stop and restart have a real severity difference worth signaling (restart comes back on its own; stop stays stopped until someone acts again). "Open docker stats" and "Stop all containers" (Teal, matching the pickers' existing command-category hue) stay available as top-level shortcuts either way, including when nothing is running. Verified the actual actions, not just that the menu renders: started a real container, restarted it through the picker and confirmed via `docker ps` that its uptime genuinely reset, then stopped it the same way and confirmed via `docker ps -a` that it exited -- left the system in the same all-stopped state it was already in before testing.

</details>
</div>

<div class="pkg-card" markdown="1">
<h4><code>bluetooth-picker.py</code> <span class="pkg-path"><code>~/.local/bin/bluetooth-picker.py</code> (<code>scripts/</code> package)</span></h4>
<p>Bluetooth device picker for waybar's bluetooth module -- self-contained on bluetoothctl, no third-party wofi/rofi tool depended on.</p>
<details markdown="1"><summary>Full details</summary>

Bluetooth device picker triggered from waybar's `bluetooth` module `on-click`, replacing `nwg-bar`'s static bluetooth.json (On/Off/Manager buttons, no device list). Same modal approach as `wifi-picker.py` deliberately -- wofi `--dmenu`, category colors, active-connection border-stand-in marker -- but fully self-contained rather than wrapping a third-party tool: checked first, and the only wofi/dmenu-adjacent Bluetooth picker that exists at all is a 3-year-stale rofi-specific AUR package (`rofi-bluetooth-git`), not worth depending on over a ~150-line direct script built on `bluetoothctl` (bluez 5.87 on this machine; confirmed via `bluetoothctl --help` that `devices Paired`/`devices Connected`/`info <mac>`/`--timeout <n> scan on` all exist and work as expected before writing anything against them -- note `paired-devices` is *not* a valid command in this bluez version, `devices Paired` is). Menu: power toggle, scan (bounded `--timeout 8` non-interactive scan, then relaunches itself to show a fresh list -- same self-relaunch pattern `networkmanager_dmenu` uses after its own rescan), Bluetooth Manager shortcut, paired devices (click connects/disconnects, whichever applies), and any device bluez currently knows about but hasn't paired with yet (`bluetoothctl devices` bare, minus the already-paired set -- populated by a scan; without this "Scan for Devices" would run a scan and then have nothing new to act on). Colors mirror `wifi-picker.py`'s categories directly: Sky for a paired device, Teal for a nearby-but-unpaired one (same meaning as `wifi-picker.py`'s "saved" Teal -- known/available, not the thing you're actively connected to), Peach for a command -- deliberately does not surface any WiFi-specific action, the same way `wifi-picker.py` now excludes the Bluetooth toggle it used to inherit from upstream (see the changelog). Selecting a nearby device pairs, trusts, and connects in one go, bounded to a 20s timeout -- most consumer audio/BLE gear uses passkey-less "just works" pairing and completes well within that, but a device that genuinely needs an interactive PIN prompt has nowhere for that prompt to go in this flow and will just time out with a message pointing at Bluetooth Manager instead. `run()` centrally catches `subprocess.TimeoutExpired` on every `bluetoothctl` call (connect/disconnect/pair can all hang waiting on a device that never responds) and turns it into an ordinary non-zero return code, rather than an uncaught traceback crashing the picker.

</details>
</div>

<div class="pkg-card" markdown="1">
<h4><code>networkmanager-dmenu</code> <span class="pkg-path"><code>~/.config/networkmanager-dmenu/</code></span></h4>
<p>Wi-Fi picker backend -- official extra-repo package, wofi as its dmenu backend, scan -> connect -> password-prompt-if-needed flow.</p>
<details markdown="1"><summary>Full details</summary>

Wi-Fi picker triggered from waybar's `network` module `on-click` -- replaced `nwg-bar`'s static wifi.json (On/Off/Settings buttons, no scan list) with a real scan → click a network → password-prompt-if-needed → connect flow, plus Wi-Fi on/off toggle and a `nm-connection-editor` shortcut, all in one menu. From the official `extra` repo, not AUR. Uses `wofi --dmenu` as its menu backend (`dmenu_command = wofi` in `config.ini`) -- confirmed via reading the tool's own source (`networkmanager_dmenu`, the Python script itself) that it has first-class wofi support, not just generic dmenu-protocol compatibility: it auto-detects `wofi` and appends wofi's own `-P`/`--password` flag for the passphrase prompt (masks input, confirmed via `wofi --help` that flag exists locally), and has wofi-specific highlight markup for the currently-connected network. Smoke-tested `wofi --dmenu` with a piped test list before wiring this up, given this repo's prior history of real wofi `--dmenu` bugs (see the `nwg-bar` row above) -- rendered a normal solid popup with no issue, since those earlier bugs were specifically about forcing a *button-grid* layout through `--dmenu`, not this tool's plain vertical list usage. List entries show icon+name only (`format = {icon}  {name}` in `config.ini`) -- no visible signal%/bars/security text, `wifi_icons` (5 Material Design strength glyphs, `U+F092F`..`U+F0928`, verified present in the installed font via `fc-query` the same way every other icon in this repo is verified) carries the strength instead. **Wofi's dmenu list has no per-item hover-tooltip support at all** (checked: no such feature exists in wofi) -- so "see full detail on hover" genuinely isn't achievable with this tool, not a partial implementation of it.

</details>
</div>

<div class="pkg-card" markdown="1">
<h4><code>wifi-picker.py</code> <span class="pkg-path"><code>~/.local/bin/wifi-picker.py</code> (<code>scripts/</code> package)</span></h4>
<p>Themed wrapper around networkmanager-dmenu -- adds category colors via monkeypatching two functions, not a fork of the ~1500-line upstream script.</p>
<details markdown="1"><summary>Full details</summary>

Themed wrapper around the installed `networkmanager_dmenu` -- waybar's `network` module `on-click` runs this instead of calling `networkmanager_dmenu` directly. Adds category-based colors (Sky for a real network, Peach for a command like Rescan/Enable/Disable/Launch-Editor, Teal for a saved connection) so the menu's different kinds of rows are visually distinguishable at a glance -- upstream only colors the single active/connected line, everything else renders identically. Loads `/usr/bin/networkmanager_dmenu` at runtime via `importlib` (`spec_from_loader` with an explicit `SourceFileLoader`, since `spec_from_file_location` can't infer a loader for a file with no `.py` extension -- returns `None` silently rather than raising, confirmed by hitting it) and monkeypatches exactly two functions (`get_wofi_highlight_markup`, `get_selection`) rather than forking the whole ~1500-line script -- every actual NetworkManager interaction still runs the real, maintained upstream code. Category is detected via `Action.func` identity (`process_ap` == a real network; `toggle_wifi`/`rescan_wifi`/`launch_connection_editor`/`delete_connection`/`show_wifi_password`/`prompt_saved` == a command) plus the `":SAVED"` suffix upstream already appends to saved-connection names -- wrapped in a `try/except AttributeError` so an upstream refactor degrades to "no color" instead of crashing the whole picker. **A real, confirmed pitfall while verifying this**: a background-launched test process reliably vanished between one tool call and the next in this remote session (`setsid ... &` in one shell invocation, checked with `pgrep` in a separate one) even though `setsid` should detach it -- the remote execution environment doesn't appear to preserve backgrounded processes across separate calls the way a persistent terminal would. This produced a false "the colors aren't rendering" result once, from screenshotting a stale/empty window. The real fix for testing this kind of thing here: launch, wait, and screenshot all within one single tool call -- confirmed correct rendering (Sky/Mauve/Teal all found via pixel search in a live window) once tested that way.

</details>
</div>

<div class="pkg-card" markdown="1">
<h4><code>mako</code> <span class="pkg-path"><code>~/.config/mako/</code></span></h4>
<p>Notifications</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>mpd</code> <span class="pkg-path"><code>~/.config/mpd/</code></span></h4>
<p>Music Player Daemon -- the actual player/backend, replacing termusic entirely. Runs as `mpd.service` (systemd --user, shipped by the package itself). See its own `README.md`.</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>rmpc</code> <span class="pkg-path"><code>~/.config/rmpc/</code></span></h4>
<p>Terminal music player UI, an MPD client -- no playback logic of its own. Paired with `music-search.py` (`scripts/` package) for immediate search/play via `yt-dlp` + `mpv` (or search/download into the library with a flag) -- no Spotify/YouTube Premium needed. See its own `README.md`.</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>kitty</code> <span class="pkg-path"><code>~/.config/kitty/</code></span></h4>
<p>Terminal, incl. the Nerd Font setting everything else depends on</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>tmux</code> <span class="pkg-path"><code>~/.config/tmux/</code>, <code>~/.tmux/scripts/</code></span></h4>
<p>Multiplexer config + the docker status-bar script</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>nvim</code> <span class="pkg-path"><code>~/.config/nvim/</code></span></h4>
<p>Editor</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>zed</code> <span class="pkg-path"><code>~/.config/zed/</code></span></h4>
<p>GUI editor</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>zsh</code> <span class="pkg-path"><code>~/.zshrc</code>, <code>~/.p10k.zsh</code></span></h4>
<p>Shell + prompt (oh-my-zsh and its plugins are bootstrapped by `install.sh`, not vendored — see below)</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>scripts</code> <span class="pkg-path"><code>~/.local/bin/</code></span></h4>
<p>Utility scripts wired into sway keybindings and the wallpaper timer</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>systemd</code> <span class="pkg-path"><code>~/.config/systemd/user/</code></span></h4>
<p>User units: daily wallpaper fetch, optional detached tmux session</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>gtk</code> <span class="pkg-path"><code>~/.config/gtk-{3,4}.0/</code></span></h4>
<p>GTK theme selection (Catppuccin Mocha)</p>
</div>

<div class="pkg-card" markdown="1">
<h4><code>xdg</code> <span class="pkg-path"><code>~/.config/mimeapps.list</code></span></h4>
<p>Default app associations (browser, image viewer, etc.)</p>
</div>

</div>



## Why some things *aren't* here

Not everything under `~/.config` is vendored. Deliberately excluded:

- **Auth/session state**: `gh`, `github-copilot`, `.claude*`, `.gemini`, browser
  profiles (`BraveSoftware`, `chromium`, `google-chrome`, `mozilla`, `zen`). These
  contain credentials or get regenerated the first time you log into each tool — they
  don't belong in a public repo and `install.sh` doesn't try to restore them.
- **Caches/generated state**: `dconf` (mostly — see below), `go`, `yarn`, `npm`,
  `pgcli`/`btop`/`lazygit` app state, `xfce4` (only contained Thunar's stock example
  custom action, not real configuration).
- **Secrets**: never committed, ever. See "Secrets" below.

If you add a new tool and aren't sure which bucket it falls into: does deleting it
lose your login, or just some cache/history you don't mind rebuilding? If the former,
leave it out.

## Secrets

Convention (already the one in the README before this was written up): anything
machine-specific or sensitive goes in a `*local` file that isn't part of any stow
package and is gitignored (`?*.local` in `.gitignore` — note the `?*`, not `*`; a bare
`*.local` glob would also match a directory literally named `.local`, which is exactly
what `scripts/.local/bin/` needs to exist as).

Example already in use: `zsh/.zshrc` ends with

```sh
[ -f ~/.zshrc.local ] && source ~/.zshrc.local
```

and `~/.zshrc.local` (not in the repo) holds `export GEMINI_API_KEY=...`. Follow the
same pattern for anything else that needs a real secret.

## `install.sh`, step by step

Entry point for a from-scratch machine (see README's Quick Start). Runs as your normal
user, `sudo` where it needs root:

1. Install `git`, `stow`, `base-devel`.
2. Clone this repo to `~/dotfiles` (or `git pull --ff-only` if it's already there —
   the whole script is meant to be re-run safely).
3. Build the package list dynamically: every top-level directory except `packages/`
   and dotfiles (`.git`, ...). This is why adding a new stow package to this repo
   needs no change to `install.sh` itself.
4. Install every package in `packages/pacman.txt`, then bootstrap `yay` if missing and
   install `packages/aur.txt`. Both use `xargs -a file command` rather than piping a
   package list on stdin — deliberate, see the changelog for why.
5. Dry-run `stow -n` against every package first, to catch anything real (not a
   symlink) already sitting at a target path — a fresh Arch install's skeleton
   `.bashrc` etc. would otherwise make the real `stow` call abort. Anything real gets
   moved to `~/.dotfiles-backup/` before the real `stow` runs.
6. `stow` everything for real.
7. `chsh` to zsh if it isn't already the shell.
8. Bootstrap oh-my-zsh (official installer, `RUNZSH=no CHSH=no KEEP_ZSHRC=yes` so it
   doesn't launch a shell or clobber the `.zshrc` stow just placed), then clone
   Powerlevel10k + the two zsh plugins referenced in `.zshrc`'s `plugins=(...)` list.
9. Clone TPM (tmux's plugin manager) if missing.
10. Download the ZedMono Nerd Font straight from its own upstream release (the URL is
    documented inside the font's own bundled `README.md` — this repo doesn't vendor
    the ~700MB of font files, since none of the standard Arch/AUR packages ship this
    particular one).
11. Bootstrap Homebrew if missing, then `brew install gh pnpm`.
12. Enable + start the services this machine actually runs (`NetworkManager`, `iwd`,
    `bluetooth`, `docker`, `power-profiles-daemon`, `ufw`); `sddm` is *enabled* but not
    started immediately, since starting a display manager mid-script would hijack the
    console you're running the script from — it takes over on the reboot the script's
    final message tells you to do anyway.
13. Add yourself to the `docker` group.
14. Enable the `wallpaper.timer` user unit.
15. Apply the GTK theme via `dconf write` — the `gtk/` package's `settings.ini` sets
    the theme *name*, but GNOME-aware apps actually read the active theme/color-scheme
    from dconf, so both need to happen for the theme to actually show up.

It has been syntax-checked, had its trickier logic (the stow conflict-detection
parser, the `.gitignore` glob, a full 13-package stow simulation against realistic
`/etc/skel` files) verified in isolated sandboxes, every package name in
`packages/*.txt` confirmed to actually resolve (`pacman -Si`/`yay -Si`), every external
URL confirmed reachable, and every systemd service name it enables confirmed to exist.
That verification pass found and fixed a real install-breaking bug: `pacman.txt` had
15 AUR-only packages duplicated into it (from how the manifests were first generated —
see the changelog), and `pacman -S` aborts its *entire* transaction if even one target
doesn't exist in the official repos, so the original file would have failed to install
anything at all on a truly fresh machine. What's still missing is a single, real,
uninterrupted run against an actual blank machine — this machine already has
everything it does in place, so a live run here would be a no-op, and that one gap
genuinely needs a spare VM or drive to close.

## exec order matters: dbus-update-activation-environment must come first

`sway/config`'s very first `exec` is `dbus-update-activation-environment --all`. This
has to run before *anything* that starts a systemd `--user` service (`swayidle.service`,
`sway-audio-idle-inhibit.service`) — those services run under the systemd user
manager, a separate process from sway with its own environment, and it has no idea
`WAYLAND_DISPLAY`/`SWAYSOCK` exist until this command imports them. Get the order
wrong and those services crash-loop with "Unable to connect to the compositor" —
happened for real once, see the changelog. If you add another systemd `--user`
service that needs to talk to sway, its `exec systemctl --user start ...` line needs
to come after this one.

Note this only matters at sway's actual startup: plain `exec` lines (unlike
`exec_always`) don't re-run on `swaymsg reload`, so testing an exec-order fix via
reload alone won't catch an actual ordering bug — it only shows up on a real fresh
login.

## Idle management: swayidle as a systemd user service, plus caffeine mode

`swayidle` (screen dimming, lock, suspend timeouts — `sway/.config/sway/idle/config`)
runs as a systemd user service, `systemd/.config/systemd/user/swayidle.service`, not a
raw `exec` line. `sway/config` starts it with `exec ~/.local/bin/swayidle-startup.sh`
rather than launching the process directly.

This exists specifically so caffeine mode — the coffee-cup icon in waybar,
`custom/caffeine` — can be trivial and reliable: on is `systemctl --user stop
swayidle.service`, off is `systemctl --user start swayidle.service`. No PID files, no
state tracking for the *live* state; systemd's own active/inactive state *is* the
caffeine state, which `caffeine-status.sh` just reads back for the waybar icon.
Stopping the whole service (rather than e.g. a `systemd-inhibit` suspend lock) is
deliberate — an inhibitor wouldn't stop swayidle's own `timeout 600 swaymsg output *
dpms off` line, since that never goes through logind at all. Only actually stopping
swayidle keeps the screen on.

### Caffeine mode surviving a reboot

Caffeine mode used to silently reset to off on every reboot, no matter what it was
left at. Root cause: `swayidle.service` is `enabled` (`WantedBy=default.target` --
confirmed via `systemctl --user is-enabled swayidle.service`), so systemd's user
manager auto-starts it at *every* login on its own, completely independent of
sway -- the plain `exec systemctl --user restart swayidle.service` line that used
to be here was reasserting "start" regardless of what caffeine mode had last been
set to, since it had no way to know.

Fixed with a tiny persisted-state file, `~/.local/state/caffeine/enabled` (present
= caffeine on, absent = off -- a marker file, not a content-parsing exercise).
`caffeine-toggle.sh` now writes/removes it alongside stopping/starting the service.
`scripts/.local/bin/swayidle-startup.sh` (what sway's `exec` line actually calls
now) is the single source of truth for swayidle's state at startup: if the marker
is present, it explicitly stops the service systemd's `default.target` just
auto-started, overriding it; otherwise it does the same `restart` this line always
did (still needed for the `dbus-update-activation-environment` ordering reason
documented right above this `exec` line -- swayidle started by systemd at login
can predate that).

Verified the actual failure mode, not just the fix: toggled caffeine on (marker
created, service stopped), manually re-triggered the auto-start systemd would do
at the next login (`systemctl --user start swayidle.service`), confirmed the
service was back to active exactly as it would incorrectly be pre-fix, then ran
`swayidle-startup.sh` the way sway's `exec` line would and confirmed it correctly
stopped the service again. Also verified the off case (no marker -> normal
restart, stays active) and that `caffeine-status.sh` reports the right state
through a full toggle sequence. Couldn't trigger a literal reboot to verify this
against a real fresh sway startup without disrupting the live session, so this
rests on an exact functional simulation of the real startup sequence rather than
an actual reboot.

An earlier version managed this with raw `pkill`/background-and-`disown` instead of
systemd, and hit a real hang: the backgrounded process ended up stuck as a direct
child of the toggle script (visible via `pstree` and `/proc/pid/wchan` = `do_wait`).
Systemd unit start/stop doesn't have that failure mode.

**The gap the entry above flagged (no real reboot to test against) turned out to
matter.** A genuine system reboot happened during a later session, and a routine
"check whole-system stability before cutting a release" sweep found
`swayidle.service` sitting `inactive (dead)` -- on a completely fresh boot, not
some leftover state. `journalctl --user -u swayidle.service -b` showed exactly
what the ordering comment above already predicted: 4 rapid failures in ~7
seconds, all `"Unable to connect to the compositor... check WAYLAND_DISPLAY"`,
before `swayidle-startup.sh` (the actual fix, `exec`'d later in `sway/config`)
ever got a chance to run. The part the manual simulation upstream missed: those
4 failures land inside systemd's default start-limit-burst (5 failures / 10s
interval), so by the time `swayidle-startup.sh`'s own `systemctl --user restart`
finally runs, the unit is already in `start-limit-hit` -- and a plain `restart`
against a unit in that state is a **silent no-op**, no error, nothing in the
script's own output to catch. Manually running `systemctl --user start` once (as
the original verification did, simulating "the next login") never reproduces
this, since one manual start attempt can't rack up 4 failures the way systemd's
own auto-restart loop does in the first few seconds of a real boot -- a genuine
example of a simulated test passing while the real trigger it stood in for still
had a live bug.

Fixed by adding `systemctl --user reset-failed swayidle.service` to the top of
`swayidle-startup.sh`, before either branch. Confirmed the theory directly before
writing the fix, not just assumed it: reproduced the dead state, ran
`systemctl --user restart` alone against it (no change, still dead, matching the
no-op theory), then `reset-failed` immediately followed by `restart` (came up
active in under a second) -- isolated proof before touching the real script.
Verified the actual fixed script afterward too: ran it live in both of its own
branches (caffeine-on -> correctly stops a freshly-reset unit; caffeine-off ->
correctly restarts and stays active), and relaunched rmpc from cold afterward to
confirm the reboot hadn't quietly broken anything else in the same session
(config/theme loaded correctly, `cache_dir` resolved, zero errors -- see the rmpc
theme entries above).

`sway-audio-idle-inhibit.service` has a real crash history of its own
(`coredumpctl list` shows several SIGABRTs across separate days, unrelated to
this reboot), but confirmed currently healthy and running since this exact boot
with no crash -- not chased further here since it isn't reproducing right now,
noted for awareness rather than fixed blind.

## The wallpaper pipeline is the ONLY wallpaper pipeline

There used to be a second, untracked script (`~/scripts/fetch-bing.sh`) firing on
every sway reload via `exec_always`, independent of the `wallpaper.timer`-driven one
below. It's gone now (see the 2026-08-23 changelog entry for the full story) --
`fetch_wallpaper.sh` via the daily timer is the only thing that changes the wallpaper.
If you ever see wallpaper-related `exec`/`exec_always` lines back in `sway/config` in
the future, that's a regression, not a feature.

## The wallpaper pipeline, and why it can't crash sway anymore

`systemd/.config/systemd/user/wallpaper.timer` fires `wallpaper.service` once a day,
which runs `scripts/.local/bin/fetch_wallpaper.sh`. The manual `output * bg ... fill`
line in `sway/.config/sway/config` only sets the background once, at sway startup —
this script is what keeps it updated day to day, and what applies it live via
`swaymsg` without needing a sway restart.

Also triggerable on demand now, not just once a day: waybar's `custom/wallpaper`
module (Rosewater icon, left of the docker module) runs this exact same script on
click, no separate wrapper. It's the same `flock`-guarded, retry/validate/fallback
pipeline either way — a manual click can't race the daily timer, and the script
picking up `notify-send` calls (fetching / success / fallback / failure) benefits
both paths, not just the button, since it used to be silent, log-file-only.

**Every click used to fetch the exact same image, though** — confirmed directly
(curled the same URL twice, compared md5sums: identical) that Bing's "wallpaper of
the day" for a fixed index+market is genuinely static for the whole day, so
`WALLPAPER_URL` being one hardcoded URL (`index=0`, `mkt=en-US`) meant every click
within a day just re-downloaded the same bytes. Also confirmed both `index` (0-7ish,
recent past days) and `mkt` (country/locale) each independently vary the actual
photo — different markets often get a different image for the same real day (tested
several: en-US/de-DE/fr-FR shared one image, en-GB had a different one, ja-JP/zh-CN
shared a third). Now `wallpaper_url()` builds the request from a random recent index
(0-3) and a random market out of ~20, re-rolled on every retry attempt too (not just
once per run), so a click is genuinely likely to differ from the last one. Not every
combination is guaranteed distinct — several markets do share images on any given
day — but verified via three real consecutive runs producing three different
md5sums, versus the old behavior's one fixed hash all day.

It's built so that no single failure — API downtime, a malformed response, no network,
or a totally fresh machine with no wallpaper history yet — can leave sway without a
background or crash `swaybg` (the helper process sway delegates background rendering
to; a bad image crashes *it*, not sway itself, but the visible symptom — background
gone, needs a reload to fix — reads the same from the outside):

1. **Network check** (`nmcli networking connectivity check`) skips a doomed attempt
   outright; not authoritative on its own, since the download's own timeouts are the
   real check.
2. **Download with retries** (3 attempts, `--connect-timeout 10 --max-time 20` so a
   flaky connection fails fast instead of hanging).
3. **Validate the response is actually an image** (`file --mime-type`, not just
   "non-empty") before it's allowed anywhere near `current.jpg` or `swaymsg`. This is
   the fix for the actual historical bug: the API occasionally returns a JSON status
   blob instead of image bytes, which used to sail straight through to `swaybg` and
   crash it.
4. **Three-tier fallback** if 1–3 don't produce a valid image: today's download →
   `.last_good.jpg` (a stable copy kept outside the `Active/`/`Archive/` rotation,
   updated only after a successful validation, so a bad day can never overwrite or
   archive it away) → a plain solid color via `swaybg -c`/`solid_color` mode, which has
   no image to parse and therefore can't itself fail. Tier 3 is what makes a from-scratch
   machine safe on day one, before any fetch has ever succeeded.

   The archiving step's `find "$ACTIVE_DIR" -maxdepth 1 -type f ...` deliberately
   uses `-type f`, which excludes symlinks — found and cleaned up 5 dead broken
   symlinks inside `Archive/` during a stability pass (dated across Jun–Aug 2026)
   that had clearly been swept in by an older version of this logic before that
   guard existed, each pointing at a plain-date `Active/wallpaper-YYYYMMDD.jpg`
   that no longer exists there (`Active/` only ever holds the current day's file).
   The current `-type f` guard means this specific kind of debris can't recur.
5. **`flock`** so the timer and a manual run can't race each other.
6. **Waits for sway's IPC socket instead of checking once** (`apply_background()`,
   up to 20s, polling every second). Found this auditing the wallpaper/lock setup
   for boot reliability: `wallpaper.timer` has `Persistent=true` (catches up a
   missed daily run on boot), but the service is only ordered `After=
   network-online.target` — nothing ties it to sway actually being up.
   `graphical-session.target` looked like the obvious fix, but checked first
   rather than assuming it'd help: `systemctl --user status
   graphical-session.target` shows it's a real loaded unit that stays
   **`inactive (dead)`** all session, since nothing in this sway config ever
   activates it -- ordering against it would've been a no-op. A single instant
   socket check could lose this race at boot: `current.jpg` gets updated on disk
   regardless, but the live `swaymsg` apply would silently give up, leaving
   *yesterday's* wallpaper showing until a reload that never happens on its own.
   The retry costs nothing in the normal case (manual click, or the timer's
   normal daily run well after login) -- the socket's already there, so it
   returns on the very first check.

7. **`After=network-online.target` in `wallpaper.service` is itself a no-op** —
   found while auditing the rest of the repo for uncoordinated config. Checked
   rather than assumed: `systemctl --user list-unit-files network-online.target`
   returns **zero unit files** on this machine — `network-online.target` is a
   system-level target, never instantiated inside the `--user` manager's own
   namespace, so ordering a user unit `After=` it is syntactically accepted but
   has nothing to actually order against (same class of silent-no-op as the
   `graphical-session.target` finding just above, different unit). Left the line
   in place rather than deleting it outright — it costs nothing and documents
   the *intent* even though it doesn't enforce it — but the real "don't run
   before the network's up" protection is entirely carried by step 1's own
   `nmcli` check plus the download's own timeouts and three-tier fallback, not
   by systemd ordering. Worth knowing if you're ever debugging why a boot-time
   catch-up run fetched a wallpaper before the network was actually ready:
   nothing was stopping it from trying, by design of this unit file, not by
   accident.

Also relevant to "does this survive a truly fresh install": `install.sh` does
`systemctl --user enable --now wallpaper.timer` *before* sway has ever started
(it's run from setup, not from inside a running session). `Persistent=true`'s
standard systemd semantics fire a catch-up run immediately in that case (no prior
trigger recorded), which reaches the `ln -sf "$FILEPATH" "$CURRENT"` line and
creates a valid `current.jpg` on disk regardless of whether the live `swaymsg`
apply succeeds -- so sway's own static `output * bg current.jpg fill` line
(`sway/config`) finds a real file the very first time sway itself starts, not a
dangling symlink. Not independently re-verified with an actual from-scratch
install in this pass (same gap the rest of `install.sh`'s verification already
has, documented above) -- this rests on standard, well-documented systemd
`Persistent=` behavior, not a fresh empirical test.

**Logging**: `~/.local/state/fetch-wallpaper/fetch-wallpaper.log` (rotated at ~1MB,
one previous copy kept) has every attempt, failure reason, and which fallback tier
fired. Also visible live via `journalctl --user -u wallpaper.service`. If the wallpaper
ever looks stale or wrong, that log is the first thing to check — it will say exactly
which of the three tiers actually ran, rather than leaving you guessing.

## The lock screen: one config, four trigger points, one dead alternate removed

`sway/.config/sway/lockconfig` is the single real swaylock config -- Catppuccin
Mocha ring/text/key-highlight colors, a big left-positioned clock/date indicator,
frosted dark backdrop, and `image=.../current.jpg` (the exact same file the
desktop background itself uses, so the lock screen never shows a different
wallpaper than what you were just looking at). Four places trigger it, all
consistently pointing at this one file:

- Manual keybind: `bindsym Mod1+Shift+semicolon exec swaylock -C
  ~/.config/sway/lockconfig` (`sway/config`)
- Idle timeout: `timeout 300 'swaylock -C ~/.config/sway/lockconfig'`
  (`sway/idle/config`)
- Before sleep/suspend: `before-sleep 'swaylock -C ~/.config/sway/lockconfig'`
  (`sway/idle/config`)
- The power menu's Lock button: `"exec": "swaylock -C
  /home/yash/.config/sway/lockconfig"` (`nwg-bar/bar.json` -- absolute path
  here specifically, not `~`, for the no-shell-expansion reason documented in
  the `nwg-bar` row above)

Auditing this for redundancy found a real one: `sway/.config/sway/scripts/lock.sh`
existed as a second, completely different swaylock invocation (small 100px plain
ring, no Catppuccin theming, no clock) -- and was referenced *nowhere* (confirmed
with an exact, non-wildcarded grep for the literal filename across the whole repo,
after an initial sloppier grep with an unescaped `.` falsely matched prose like
"padlock shape"). Dead code left over from an earlier design, silently diverging
from the one lock screen everything else actually uses. Deleted, and re-stowed to
clean up the now-dangling `~/.config/sway/scripts/lock.sh` symlink it left behind.

## Volume and brightness: real controls, not nwg-bar buttons

Both used to be `nwg-bar` button popups (`volume.json`, and no popup at all for
brightness). Neither belongs in a button grid -- adjusting volume/brightness is
fundamentally a "drag to a value" interaction, and `nwg-bar` categorically can't
render one (buttons only, confirmed reading its Go source). Replaced with:

- **`pulseaudio` waybar module**: click = mute/unmute (`sway/.config/sway/scripts/volume_osd.sh
  mute-toggle`), right-click = `pavucontrol` (a real GTK mixer with per-device drag
  sliders and separate Playback/Recording/Output Devices/Input Devices tabs -- this is
  where output *and* microphone device selection actually happens, for free, and it
  already renders in Catppuccin Mocha since the GTK3 theme is applied system-wide, no
  extra CSS needed), scroll = +-5% (`volume_osd.sh +5%`/`-5%`).
- **`backlight` waybar module**: click = `scripts/.local/bin/brightness-slider.sh`, a
  `zenity --scale --print-partial` dialog -- `--print-partial` streams the live value
  on every drag frame, piped into `brightnessctl set "${value}%"` per line, so it's a
  genuine real-time slider rather than a set-once popup. Needs `zenity` (in
  `packages/pacman.txt`, official `extra` repo). Scroll = +-5%
  (`brightness_osd.sh`), unchanged.
- Both `volume_osd.sh` and `brightness_osd.sh` (`sway/.config/sway/scripts/`) are
  shared between the `XF86Audio*`/`XF86MonBrightness*` keybindings *and* the waybar
  scroll bindings now, so there's exactly one place that fires the progress-bar mako
  notification for each, not two copies drifting apart. `volume_osd.sh` also
  auto-unmutes before applying a delta (raising/lowering volume should always be
  audible) and gained a `mute-toggle` mode used by both the `XF86AudioMute` key and
  the waybar click. `XF86AudioMicMute` was added alongside it
  (`pactl set-source-mute @DEFAULT_SOURCE@ toggle`) -- there wasn't a microphone-mute
  keybinding at all before.

### The scroll flood, and why on-scroll needs `smooth-scrolling-threshold`

Scrolling on the volume/brightness pills looked broken -- confirmed via
`/tmp/waybar.log`, which had 249 lines of `Connection failure: Connection
terminated` and `Value "" of hint "value" could not be parsed as type "int"` after
one scroll session. Root cause, found in waybar's own man pages
(`man waybar-pulseaudio`, `man waybar-backlight`): defining `on-scroll-up`/
`on-scroll-down` "replaces the default behaviour" *and* neither module had
`smooth-scrolling-threshold` set (default is unset/0). A touchpad emits continuous
fractional scroll deltas (kinetic/smooth scrolling), not one discrete tick per
gesture -- with the threshold at 0, waybar fired the script on every single delta,
so one real scroll gesture spawned dozens of `pactl`/`brightnessctl`/`notify-send`
processes within milliseconds, flooding mako's D-Bus connection and racing each
other reading volume/brightness mid-write. Fixed by adding
`"smooth-scrolling-threshold": 1` to both modules, so waybar accumulates a full
scroll unit before firing once.

**Forcing the same burst manually (30 concurrent invocations) also surfaced a real,
separate danger**: `pactl set-sink-volume @DEFAULT_SINK@ +5%` does **not** clamp at
100% on its own -- the 30-way race drove the sink to 1494% (confirmed no audio was
actively playing at the time, via `pactl list sink-inputs short`, so nothing was
physically blasted, but it would have been audible/damaging if something had been).
`brightnessctl` does self-clamp (`set 1000%` lands at exactly 100%, confirmed by
testing), so no equivalent overdrive risk there, but concurrent calls can still
stack out of order. Both scripts now serialize their read-current -> compute-target
-> apply sequence behind `flock` (`/tmp/volume_osd.lock` / `/tmp/brightness_osd.lock`),
and `volume_osd.sh` computes and clamps the target to 0-100 itself rather than
trusting pactl's relative math. Re-ran the identical 30-concurrent-call burst after
the fix: clamps land exactly at 100%/0% instead of overshooting, and the waybar log
stayed at zero errors.

## Capslock/numlock: custom modules, and toggling them needs ydotool

Started as waybar's built-in `keyboard-state` module, replaced with
`custom/capslock`/`custom/numlock` (backed by `scripts/.local/bin/
keylock-status.sh` and `keylock-toggle.sh`) once click-to-toggle and a
hover tooltip were wanted -- the built-in module has neither `on-click`
nor `tooltip` anywhere in its config schema (confirmed: `man
waybar-keyboard-state` lists every option it accepts, click/tooltip
aren't among them), so no amount of CSS or config could make it
clickable. A custom module can do both, same `{text,class,tooltip}` JSON
pattern already used for `custom/caffeine`/`custom/docker`.

**Reading state** (`keylock-status.sh capslock|numlock`): reads
`/sys/class/leds/*::capslock/brightness` / `*::numlock/brightness`
directly -- the same real kernel LED state the built-in module read via
libevdev, not a cached or derived value. Confirmed live against actual
state at the time (numlock was genuinely on, capslock genuinely off) and
the script reported both correctly.

**Toggling state** (`keylock-toggle.sh capslock|numlock`) is the part
that needed real investigation. `wtype -k Caps_Lock` -- already used
elsewhere in this repo, e.g. the scroll-flood stress test -- does **not**
actually toggle the real lock state on this compositor: confirmed by
checking `/sys/class/leds/*::capslock/brightness` stayed `0` straight
through a `wtype` press. wtype injects through the
`virtual-keyboard-unstable-v1` Wayland protocol, which apparently doesn't
drive the same XKB lock-latch state machine a real key event does here.

Fixed with `ydotool` instead (official `extra` repo, added to
`packages/pacman.txt`) -- it injects through `/dev/uinput`, a genuine
kernel-level virtual input device indistinguishable from real hardware to
the same libinput → xkbcommon pipeline that processes actual keypresses,
so it correctly drives the real lock state. Confirmed the package ships
its own systemd **user** service (`ydotool.service`, no root needed at
runtime) and its own `udev` rule for `/dev/uinput` permissions (checked
the package's file list on the Arch package page before trusting this,
rather than assuming) -- a clean, standard setup, not a security-loose
workaround.

**Not yet installed on the live machine** -- needs:

```bash
sudo pacman -S ydotool
sudo udevadm control --reload-rules && sudo udevadm trigger
systemctl --user enable --now ydotool.service
```

`keylock-toggle.sh` checks for both `ydotool` being installed and
`ydotool.service` being active before attempting anything, and
`notify-send`s the exact fix (which of the two commands above is
missing) rather than failing silently or with a cryptic `ydotool` error
if clicked before this setup is done. Verified this fallback path
directly (`sh -c` invocation matching exactly how waybar calls it) --
exits cleanly with the right message, doesn't crash.

Keycodes: `58` (capslock), `69` (numlock) -- Linux's standard
`input-event-codes.h` values, cross-confirmed against
`waybar-keyboard-state`'s own documented `binding-keys` default
(`[58, 69, 70]`, i.e. capslock/numlock/scrolllock in that order).

**Cursor**: no explicit CSS needed -- waybar shows a pointer cursor
automatically for any module with an `on-click` handler (standard GTK
`EventBox` behavior), same as every other already-clickable pill in this
bar (docker, caffeine, network, pulseaudio, bluetooth). This is a
different code path entirely from the wofi popups' cursor limitation
documented elsewhere in this file -- that one is wofi's own dmenu list
never requesting a cursor-shape change at all, which is unrelated to how
waybar's own pill modules behave.

## System-wide dark mode, a waybar toggle, and Papirus (+ Catppuccin folders)

Asked to make sure the desktop is dark by default, add a waybar toggle for
light/dark, and add a well-regarded icon pack. Checked before building
anything: dark mode was already substantially in place --
`gtk-application-prefer-dark-theme=1` in both `gtk/.config/gtk-{3,4}.0/
settings.ini`, and `install.sh` already wrote `color-scheme=prefer-dark` +
the dark `catppuccin-mocha-mauve-standard+default` GTK theme to dconf.
What was actually missing: no icon theme was ever set at all (falls back
to whatever the system default resolves to), and there was no way to
switch modes without hand-running `dconf write` commands.

**Icon pack**: `papirus-icon-theme` (`packages/pacman.txt`, official
`extra` repo -- genuinely the most widely-used general-purpose Linux icon
theme, not just an assumption; it's the one most distros that ship a
curated icon set default to). Paired with `papirus-folders-catppuccin-git`
(`packages/aur.txt`) to recolor its folder icons to match this desktop's
existing Mauve accent -- verified this is the real package name and a
legitimate, actively-maintained one before adding it: an earlier guess
("catppuccin-papirus-folders") doesn't exist on the AUR at all, found by
querying the AUR RPC API directly (`aur.archlinux.org/rpc/v5/search/...`)
rather than trusting memory; the real package
(`papirus-folders-catppuccin-git`) is maintained by the official
`catppuccin` AUR account, matching the upstream
`github.com/catppuccin/papirus-folders` project.

`papirus-folders`'s actual color-switch command needs root *every time it
runs* -- confirmed by reading its own source (`_is_root_user`, re-execs
itself via `sudo` when not already root) before assuming it'd work as a
casual click-to-toggle action. So folder recoloring happens once, for
both palettes, in `install.sh` (`sudo papirus-folders -C cat-mocha-mauve
--theme Papirus-Dark` and the `cat-latte-mauve`/`Papirus-Light`
equivalent), right where `sudo` is already in use for other steps --
never at runtime. `catppuccin-gtk-theme-latte` also added to
`packages/aur.txt`, the light-flavor counterpart to the already-installed
`-mocha` package -- without it, "Papirus-Light"/`prefer-light` would have
nothing but Adwaita to fall back to, and the toggle below would be real in
name only.

**The toggle**: `scripts/.local/bin/theme-status.sh` (waybar `custom/
theme` module, positioned left of the wallpaper button in
`modules-right`) + `theme-toggle.sh` (its `on-click`). Pure `dconf`
reads/writes -- no state file, unlike `caffeine-toggle.sh`'s pattern,
deliberately: dconf already persists across reboots on its own (it's a
real database), so a second copy of "which mode is active" here would
just be one more thing that could silently drift from the truth, the
same reasoning already applied to `keybind-search.py`'s live-parsed
config over a maintained list. Verified the actual toggle, not just that
it runs without error: ran it, confirmed via `dconf read` that
`color-scheme`/`gtk-theme`/`icon-theme` all flipped to the light-mode
values, screenshotted and found the waybar icon's color actually changed
(Sapphire moon -> Yellow sun), then toggled back and confirmed dark
again -- left the real system in dark mode (the intended default)
afterward, not mid-test.

**Scope, stated plainly rather than left implicit**: this covers every
app that reads the standard GNOME/GTK dconf keys automatically -- file
managers, browsers' native GTK chrome, settings dialogs, most GTK3/GTK4
apps -- which is the actual mechanism behind "apps detect OS dark mode."
It deliberately does **not** touch this desktop's own bar/launcher/
notification styling: waybar, wofi, and mako's `style.css` files, and
sway's window border colors, are all hand-built throughout this entire
repo to one specific Catppuccin Mocha palette. That's a deliberate design
choice already made and extensively worked on in this session (the wofi
"glass" pass, the notification icon pass, etc.), not an oversight --
making all of it respond to a generic light/dark toggle would mean
maintaining a full parallel light variant of every custom stylesheet in
this repo, well beyond what was asked here. Also disclosed rather than
silently assumed away: dconf changes apply live to already-running apps
that subscribe to `gsettings-changed` (most modern GTK apps do), but some
only read theme state once at their own startup and won't visibly change
until relaunched -- a standard limitation of this whole mechanism, not
something this script can fix.

Not wired up: Qt app theming (`QT_QPA_PLATFORMTHEME`/`qt6ct`). `qt6ct` is
in `packages/pacman.txt`, but checked and found nothing in this repo
actually exports `QT_QPA_PLATFORMTHEME` or has a `qt6ct.conf` -- and
neither `beekeeper-studio-bin` nor `bruno-bin` (the only two GUI apps in
`packages/aur.txt` that might plausibly be Qt) are actually Qt apps, both
are Electron. The installed `qt6-*` packages are almost certainly pulled
in as dependencies for something else, not for a Qt app in regular use.
Given no real Qt app to verify against, left this alone rather than
hand-configure `qt6ct.conf` blind -- a real, disclosed gap if a Qt app is
ever added to this setup later, not something silently papered over.

## Wofi text readability: two dead ends before the real fix

Asked again to make wofi text more readable against the glass background
("black instead of white, hard to notice"), after the icon investigation
above concluded the actual visible white patch wasn't text at all. This
time it genuinely was about `#text`'s color, and two reasonable-looking
attempts to fix it directly failed before finding the real cause:

1. **Literal black text** (`#05050a` + a light `text-shadow` glow for
   safety): measurably worse, not better. This window's own base tint
   (`background-color`) is already near-black, so near-black text has
   essentially zero contrast against *it specifically*, independent of
   whatever's blurred behind the window. Confirmed by screenshotting and
   finding the text pixels barely distinguishable from the window
   background at all -- worse than the original light color, which at
   least contrasted reliably against the dark base tint even when it
   struggled against bright patches of the blur.
2. **Subtitle-style outline** (bright fill + dark `text-shadow` ring
   around it -- the actual standard technique for text over a variable-
   brightness backdrop, e.g. video subtitles): also didn't work, for a
   different and more fundamental reason -- `text-shadow` parses without
   any error in this GTK/wofi build but doesn't actually render at all.
   Confirmed by forcing a stress-test bright background (where an outline
   shadow, if working, would produce plenty of dark pixels against the
   bright fill and bright forced background) and finding zero dark pixels
   anywhere in the window.

**The real fix** attacks the actual cause instead of the symptom: at the
previous `0.62` window background alpha, enough of the blurred wallpaper
showed through to wash out text specifically on brighter parts of it.
Raised to `0.85` -- doesn't remove the blur (SwayFX's `layer_effects` blur
on wofi's layer surface, added earlier, is still genuinely active), just
reduces how much of its brightness variance can bleed through, giving
text a far more consistent backdrop. Paired with moving `#text`'s color
from `#A6ADC8` (Subtext0, fairly muted) to `#CDD6F4` (Catppuccin "Text",
the same bright value mako already uses for its own primary text) for
extra contrast margin. Net effect: less see-through glass than before,
which is a real, disclosed tradeoff of prioritizing readability here --
worth knowing if the balance ever needs to shift back the other way.

## App launcher icons: gap, and a dark backing (not a text-color bug)

Asked for a gap between the app icon and name in drun mode ("too close"),
and for wofi to use black instead of white there. The gap was real and
simple: `#img` (confirmed a real, matching CSS node -- tested directly
with a temporary bright `background-color` that visibly applied, not
assumed from wofi's docs) had no spacing at all before this;
`margin-right: 10px` fixes it, same margin-on-the-child technique already
used for entry gutters just above it in the same file.

The color part turned out not to be a text-styling bug at all, worth
recording precisely because it looked like one at first. Found a genuine
near-white patch in a screenshot and assumed it was `#text` rendering
unstyled -- checked with `!important` on `#text`'s `color` (would win
over literally any competing rule, including the system GTK theme's own
stylesheet) and it had zero effect; checked with a bare `label { color:
... }` type selector (would catch the label regardless of what ID wofi
actually gives it) and that had zero effect either. Isolated the patch by
its exact shape and position instead of continuing to guess at selectors,
and found it sitting precisely where the icon renders, not the label --
it's real app icon pixel data. Raster icon images aren't recolorable by
CSS `color` at all (that only works for symbolic SVG icons using
`currentColor`), so no stylesheet change could ever have "fixed" this the
way a text-color bug would be fixed.

What *is* fixable: many real icons ship with an opaque or lightly-padded
white/light background meant for a light UI, which reads as a jarring
white square floating on this desktop's dark glass background with
nothing behind it. Gave `#img` a dark, rounded backing (`rgba(17,17,27,
0.5)`, `border-radius: 8px`) -- the same treatment app grids like GNOME
Activities or macOS Spotlight use for this exact reason. This only helps
icons with real alpha transparency around their edges (a background can't
paint over pixels the icon itself already drew opaque) -- confirmed this
directly rather than assuming full coverage: near-white pixel count in a
screenshot was 206 before and 209 after, i.e. genuinely unchanged for
icons with a fully opaque background baked in, which is a real, disclosed
limitation of this fix rather than something to claim as fully solved.

## Wofi color-palette consistency audit

Asked to make sure every wofi popup follows the same color palette, plus a
general look for bugs/improvements. Audited every script that invokes wofi
or embeds Pango markup in what it feeds to wofi
(`wifi-picker.py`, `bluetooth-picker.py`, `keybind-search.py`,
`wofi-calc.sh`) and the shared `style.css`/`config` themselves.

Most of it already checked out: `wifi-picker.py` and `bluetooth-picker.py`
already share the exact same three-color Catppuccin Mocha system (Sky
`#89DCEB` for a connectable/primary entity, Teal `#94E2D5` for known-but-
passive, Peach `#FAB387` for a command/action) and the exact same
`#313244` surface color wofi's own `#input` CSS uses (`rgba(49,50,68,...)`
== `#313244` -- same underlying color, just expressed differently in each
place) -- confirmed by reading through both scripts fully rather than
just grepping for hex codes and assuming they matched.

Two real things found and fixed:

- **A duplicate color, not just a stylistic one**: `bluetooth-picker.py`'s
  "Enable Bluetooth" entry (the only one shown when Bluetooth is powered
  off) used a hardcoded `foreground="#FAB387"` span instead of `markup(...,
  "command")` -- the same value CATEGORY_COLORS already defines, just
  copied instead of referenced. Harmless today, but exactly the kind of
  second copy of a value that silently drifts out of sync if the palette
  ever changes, the same failure mode documented for the TPM plugin-path
  split earlier in this file. Fixed to read from the shared dict.
- **`keybind-search.py` had zero color-coding at all** -- the one wofi
  popup in this desktop with real, distinct categories (Sway vs. Tmux
  entries) and no visual way to tell them apart at a glance, unlike every
  other multi-category picker. Added `SOURCE_COLORS` (Sky for Sway, Teal
  for Tmux, same hues as the other two pickers) coloring just the source
  tag, plus Peach for the `[scope]` suffix (matching Peach's established
  "this needs an extra step/context" meaning from the other pickers'
  command category) -- colored only the tag, not the whole line like
  the free-text pickers do, since this tool's structured columns
  (tag/keys/description/scope) would lose readability if everything were
  tinted at once.

  This addition carried a real risk worth verifying properly rather than
  assuming: `keybind-search.py` is the only wofi popup in this desktop
  using `--matching fuzzy` (the others use wofi's default "contains"),
  and fuzzy matching against a string that now contains literal
  `<span foreground="...">` markup tags could plausibly search against the
  tag text itself, not just what's visually shown. Verified this doesn't
  happen with a controlled, unambiguous test rather than eyeballing a
  screenshot: piped a small set of markup-containing dmenu entries
  directly into wofi, typed a query that only matches one entry's visible
  (non-markup) text via `ydotool`, and confirmed via the actual selected/
  copied output that wofi picked the right entry -- fuzzy matching
  operates on the rendered text, markup tags don't leak into the search
  space. Reconfirmed against the real script afterward (`ydotool`-typed
  "reload tmux", correctly selected and copied the Tmux reload entry with
  its Teal tag intact).

## keybind-search.py: truncating descriptions, since wofi can't wrap or ellipsize them

Reported the keybind search popup's right side overflows. Real cause: a
couple of the sway descriptions this tool builds are enormous -- the
exit-sway confirmation's full swaynag message came out to 243 characters
end to end, roughly 1750px at this font, nearly 1.5x the entire 1152px
(60%) window width. wofi has no CSS or config-level ellipsize/wrap for
`--dmenu` entries -- checked `--help` and the binary's own exported
symbols directly (`strings $(which wofi) | grep -i wrap` does show
`gtk_label_set_line_wrap`, so wofi's own source calls it *somewhere*, but
nothing exposes control over it here, and it plainly wasn't applying to
these rows regardless).

Truncates in `keybind-search.py` itself instead (`MAX_DESC_LEN = 78`,
appends `…` when cut) -- not just to stop the overflow, but because even
if wofi *did* wrap instead of overflow, a giant multi-paragraph entry in
a quick-reference list would be its own readability problem. 78 chars
keeps every real description on one line within the window width with
room left for the longest `[scope]` suffix (`resize mode (Super+Ctrl+r
first)`), chosen by checking the actual longest entries that needed to
stay intact (the OSD scripts' descriptions) rather than picking an
arbitrary round number.

Verified two ways: the longest entry after truncation is 123 characters
(was 243), and pixel-checked the popup's right edge in a screenshot --
nothing beyond background-level intensity 2px past the window boundary,
versus real elevated (border) values right at the edge itself.

## A real bug: the left border was invisible on every entry, always

Reported that left and right edges of rows/cells weren't visible properly.
Real bug, not a perception issue: an earlier revision (the one that first
added a border to every entry) also added `border-left: 2px solid
transparent;`, declared *after* the main `border` shorthand specifically
so it would win on just that one edge -- reserving 2px of space for a
selected-state accent bar without a layout jump when it appeared. That
made the left edge invisible on *every* entry at rest, not just
unselected ones, which is the actual bug: in the app launcher's grid, one
cell's visible right border sitting next to the adjacent cell's invisible
left border reads as a broken, asymmetric gutter rather than a clean
framed gap -- exactly "can't see left and right edges properly."

Fixed by removing the border-left override entirely and keeping border
*width* constant (1px) across idle/hover/selected -- selected state now
differentiates by color alone (full-strength `#CBA6F7` instead of a raised
alpha), which needs no layout-jump guard at all since nothing changes
size, only color. Simpler than what it replaced, not just a bug fix.

Verified by pixel-comparing a cell's right border against its neighbor's
left border at the same row: both sides now render the same color
consistently (e.g. `(70,62,88)` on both, at multiple rows) -- symmetric,
not just "present."

## music-search.py: real thumbnails in the results list

Reported directly: "only text doesn't make that much sense, show
thumbnail and title in each row" -- a fair point, a title-only list
doesn't actually tell you much about a video the way seeing its
thumbnail would.

wofi's own `img:` dmenu markup handles this directly (`--allow-images`,
the exact same mechanism `notification-history.py` already uses
elsewhere in this repo) -- nothing bespoke needed. The only real
question was where to get a thumbnail image cheaply: yt-dlp's own
`--flat-playlist` JSON does include a `thumbnails` array, but every URL
in it carries a signed, per-request query string (confirmed by reading
one directly) -- not something worth depending on staying valid or
parsing correctly. YouTube's plain, unsigned
`https://i.ytimg.com/vi/id/mqdefault.jpg` URL shape (320x180, ~11-18KB)
resolves reliably without needing any of that (confirmed directly with
a real `curl`, not assumed from convention), so that's what's used
instead -- one fixed, well-known pattern, not something parsed out of a
response.

Fetched for all ~10 results concurrently (`ThreadPoolExecutor`) rather
than one at a time -- confirmed directly this matters: ~0.4s for all 10
fetched together versus what would have been several seconds doing them
serially. Downloaded into a per-run temp directory
(`tempfile.mkdtemp`), cleaned up unconditionally after the picker
closes either way (picked a result or cancelled) -- these files only
ever needed to exist long enough for wofi to read them while the list
was open.

Verified live, not just "should render": checked the temp directory's
actual contents *while* the real results wofi popup was open (triggered
through the real `$mod+Shift+y` keybinding with real typed input, not
the script run manually) -- ten real, valid JPEG files, one per result,
confirmed with `file` directly rather than just trusting they existed.

## termusic removed entirely: mpd + rmpc instead

Direct feedback once it was clear termusic's search was going to stay
broken for the foreseeable future (the public Invidious network it
depends on, see the entries below): *"termusic isn't of any use then,
lets use a better tui or cli local music player then and remove this
damn termusic."* Rather than keep patching around termusic's one real
problem forever with `music-search.py` doing all the actual useful
work, the player itself got swapped out too.

**`termusic/` is gone from this repo** -- `~/.config/termusic/`
unstowed and deleted, package uninstalled
(`sudo pacman -R termusic`), `termusic-toggle.sh` removed. Every entry
below this one that talks about termusic is left exactly as it was
written -- real history of real bugs found and fixed at the time, not
rewritten to pretend termusic was never here. The **Package map**
above reflects the current, actual state (`mpd`/`rmpc`), not history.

**`mpd`** (official `extra` repo, `mpd.service` shipped by the package
itself -- no unit file needed in this repo) is now the actual player.
This is a real architectural improvement, not just a different UI on
the same risk: MPD has zero third-party API dependency of any kind, it
only ever plays real files already sitting in `music_directory` --
there's no equivalent "public instance network could go dark" failure
mode the way termusic's Invidious-based search had. Confirmed MPD's own
filesystem watcher (`auto_update "yes"`) actually works, not just
trusted the option's name: dropped a file into `~/Music` with zero
clients connected and watched it get indexed within seconds in MPD's
own log -- a real improvement over termusic, which had no such watcher
at all (confirmed by reading its source, back when it was still here).

**`rmpc`** (also official `extra` repo, 3.3k GitHub stars, actively
maintained, its own tagline: *"A beautiful and configurable TUI client
for MPD"*) is the new UI. A genuinely validating find while picking it:
rmpc ships its **own** yt-dlp-based YouTube downloader
(`shared/ytdlp/` in its source, confirmed by reading it directly --
real yt-dlp, not Invidious) -- independent proof the same approach
`music-search.py` already took was the architecturally sound one, not
just a workaround invented here. rmpc's own CLI picker for it uses a
plain text list with no thumbnails though, so `music-search.py` stays
the actual search tool -- rmpc just plays whatever lands in `~/Music`
afterward.

**Theme, sizing, transparency, toggle -- all rebuilt for rmpc, applying
what termusic's own setup already taught rather than rediscovering it**:
- Theme built the same "read the tool's own real defaults, don't guess
  the format" way as termusic's theme was -- `rmpc theme` dumps rmpc's
  actual default (confirmed this is genuinely how it bootstraps a
  custom theme), which turned out to be one deeply nested RON structure
  with named colors ("blue", "yellow", "black", ...) woven through the
  entire layout definition, not a separate flat palette the way
  termusic's was. Every occurrence systematically substituted for its
  Catppuccin Mocha hex equivalent -- `"blue"` specifically mapped to
  Mauve (`#cba6f7`), not Catppuccin's own literal Blue, since "blue" is
  the color rmpc's own default theme uses for every "this is active/
  current/selected" role, exactly Mauve's existing role everywhere else
  in this desktop.
- `background_color`/`header_background_color` left `None` from the
  start this time -- applying termusic's own hard-won lesson
  (`Color::Reset`/no explicit paint lets kitty's `background_opacity`
  actually blend) immediately rather than shipping an opaque background
  and rediscovering the exact same bug a second time. Verified live:
  screenshotted the real running window and found zero pixels of any
  solid background color, Mauve clearly dominant across borders
  (~26,000 matching pixels) -- the glass effect worked on the very
  first real launch.
- Sizing (`1152x540`, 60%/50% of the real `1920x1080` output) and the
  scratchpad-based toggle (`rmpc-toggle.sh`) are close to line-for-line
  the same mechanism already proven for termusic -- no reason to
  redesign what was already verified working, MPD's own daemon/client
  split just makes the "hiding the window never stops playback"
  guarantee even stronger than termusic's client/server split was
  (MPD keeps running with *zero* clients connected at all, not just a
  hidden one).

**A real image-protocol scare, resolved by finding the actual cause
rather than assuming the setup was broken**: `rmpc debuginfo`, run
directly in this same non-interactive session, reported the album-art
protocol as `Block` (a crude ASCII fallback) instead of `Kitty` --
despite `$KITTY_WINDOW_ID` and `$TERM=xterm-kitty` both being set.
Traced it to the actual cause before assuming a real bug: `tty` in this
exact session reports "not a tty" -- the environment variables are
inherited from a parent process, but this session's own shell was never
attached to a genuine terminal device, which is what kitty's graphics
protocol actually needs regardless of which env vars happen to be set.
Checked rmpc's *own* log from the real, actual launch path instead
(`kitty --class rmpc -e rmpc`, the same command the real keybinding
uses) and found `resolved_backend="Kitty"`, `kitty_graphics="true"` --
the real graphics protocol is genuinely active for the path that
actually matters, the failed detection was purely an artifact of how
this one diagnostic command happened to be run.

## rmpc's floating window: actually glass, not just technically transparent

Direct feedback right after the migration above: "lets make its
background glass like." The theme already had `background_color: None`
(carried over proactively from termusic's own transparency fix, see
below), and kitty's global `background_opacity 0.85` was blending
against it -- technically working, but not perceptibly so on a window
this large (1152x540 at the time, over half this machine's screen). A
subtle blend that reads fine on a small popup (wofi, mako) is much
easier to miss on something covering that much of the display.

**First attempt, since revised**: tried lowering opacity per-window
(kitty's `-o background_opacity`), reasoning more transparency would
mean more glass. Chasing a trustworthy number this way surfaced a real
methodology trap worth recording: whole-window pixel averaging against
a same-position wallpaper-only screenshot gave noisy, sometimes
backwards-looking deltas between opacity values (skewed by however
much text/UI happened to be on screen at capture time), until narrowed
down to sampling one fixed, confirmed-empty patch of the window at the
real toggle-triggered position instead -- that gave a clean, real
signal (a measurable, reproducible shift per opacity value). But even
with a clean signal, the fix was aimed at the wrong variable: at low
opacity, what showed through was the wallpaper completely *sharp* and
unblurred -- correctly measurable as "more transparent", but reading as
"see-through window", not glass.

**Second, direct follow-up**: "lets make its background glass like
blury... increase it size follow the 60 percent width and increase the
height accordingly" -- named the missing piece directly: blur.
Confirmed this machine runs SwayFX (`sway --version` -> `swayfx 0.6`,
not plain sway), which adds real compositor-level GLES2 blur -- already
in use for wofi via `layer_effects` (see the wofi section below), just
not yet wired up for rmpc. Read SwayFX's own README (extracted from the
cached AUR build tarball, not guessed) to confirm the exact mechanism
for a plain toplevel window rather than a layer-shell surface: `blur`,
`corner_radius`, and `shadows` are all regular `for_window`-settable
properties for ordinary windows (no `layer_effects` block needed --
that's specifically for layer-shell surfaces like wofi/waybar/mako,
matched by namespace), so `blur enable` was added directly to rmpc's
existing `for_window [app_id="^rmpc$"]` rule in `sway/config`.
`corner_radius`/`shadows` weren't set there since rmpc already inherits
the *global* `corner_radius 12` / `shadows on` defaults every ordinary
window gets -- only wofi needed its own explicit values, since layer-
shell surfaces are exempt from those per-window toplevel defaults.

Deliberately did **not** set `blur_xray`, unlike wofi's rule -- SwayFX's
own README says so explicitly for regular floating windows ("You
probably want to set this to disable :)"), since `blur_xray` is for
layer-shell panels that need to blur the *true desktop background*
specifically; a floating window blurring whatever's actually behind it
(the wallpaper, since this one is centered above everything) is already
the right result.

With real blur doing the work, the earlier per-window opacity override
became unnecessary and was removed -- `rmpc-toggle.sh` now launches
plain `kitty --class rmpc -e rmpc`, back on kitty's global 0.85. That
number turned out to already match the desktop's own established
"real glass" ratio: `wofi/style.css`'s own working glass panel also
runs its background at 0.85 alpha, paired with real blur -- mostly
opaque, with a blurred (not sharp) wallpaper hint behind it, not a
mostly-see-through window. The earlier low-opacity investigation wasn't
wasted, though: it's what proved `background_color: None` +
`background_opacity` blending was wired correctly at all, before blur
turned that correct-but-weak signal into an actually convincing one.

**Verification**, done with a cleaner test than the earlier
whole-window/empty-patch approaches: screenshotted the live window and
the identical screen region with the window hidden (`scratchpad show`
toggling it away and back), found the highest-texture 40x40 pixel block
in the wallpaper-only shot (real edge detail, luminance swinging ~4 to
~151 -- picked programmatically, not by eye, specifically so the test
has real detail to blur), then compared local horizontal-gradient
energy in that identical region between the two shots: 9.85
(wallpaper, sharp) vs. 0.83 (through the window) -- a ~92% drop -- and
the actual rendered pixels there were a smooth, consistent blended tone
(~24, 33, 46), not the sharp original texture and not a flat theme
color either (confirming it's genuine alpha-blended blur, not a solid
pane happening to sit there). Text legibility reconfirmed via a direct
ASCII luminance dump of real rendered text with both blur and 0.85
active -- glyphs stayed crisp and high-contrast.

**Size**: the same follow-up request also asked to keep the window at
60% width (already was: 1152 of 1920) and grow the height to match,
rather than the original 50%. Changed `resize set 1152 540` to
`resize set 1152 648` (1080 * 0.6) in the same `for_window` rule --
confirmed live via `swaymsg -t get_tree` showing the real window's rect
at exactly `1152x648`, centered.

## Every popup closes on Escape -- rmpc's floating window was the one real gap

Direct feedback: "all popup modals should also hide when esc key is
pressed as well." Audited every popup this desktop has rather than
assuming which ones needed fixing:

- **Every wofi-based popup** (`toggle-popup.sh`'s clients: launcher,
  calc, clipboard, emoji, wifi, bluetooth, docker, notification
  history, keybind search, music search) -- already closed on Escape,
  confirmed by the comment already in `toggle-popup.sh` from when it
  was built: wofi handles this itself natively, sway was never
  intercepting or needing to intercept that key for these.
- **nwg-bar (power menu)** -- tested live rather than assumed: opened it
  via the real `$mod+Shift+p` path, sent a real synthetic Escape
  keypress (`ydotool key 1:1 1:0`, keycode 1 = Escape), confirmed the
  process exited and `toggle-popup.sh`'s own marker file was cleaned up
  -- already correct, GTK's native handling again, no fix needed.
- **rmpc's floating window** -- tested the same way, and this one really
  was broken: focused the window, sent the same synthetic Escape, and
  it stayed open. Root cause: rmpc's own `config.ron` already binds
  its Esc key entry to `Close` under `keybinds.navigation`, but that's rmpc's own
  internal action for closing a modal *inside* rmpc (a save-playlist
  prompt, etc.) -- it has no idea sway's scratchpad exists, so with no
  internal modal open, Escape was a no-op as far as the window's
  visibility was concerned.

Fixed with a new dedicated script, `rmpc-hide.sh` (just
`swaymsg '[app_id="^rmpc$"] scratchpad show'`, the same hide rmpc-
toggle.sh's second press already does), wired in via a **per-window**
kitty keybinding override on rmpc's own launch line only:
`-o "map escape launch --type=background $HOME/.local/bin/rmpc-hide.sh"`
-- rebinds Escape for this one kitty instance before it ever reaches
rmpc's pty, `kitty/kitty.conf`'s own global map table untouched. A
separate script rather than inlining the `swaymsg` call directly in
that `-o` value: the value already needs one layer of shell quoting to
reach kitty as a single argument, and nesting `[app_id="^rmpc$"]`'s own
quotes inside that is exactly the kind of thing that goes silently
wrong instead of erroring loudly -- a real script file sidesteps it.

Verified live end-to-end through the real mechanism, not just that the
override was accepted: killed the running rmpc, relaunched via the real
`$mod+Shift+m` keybinding, confirmed via `swaymsg -t get_tree` the
window was visible, focused it, sent a synthetic Escape, confirmed
`visible` flipped to `false` -- and confirmed the rmpc process itself
was still alive and `mpd.service` still active (hiding never touches
either, exactly like every other press of the same keybinding). Then
toggled it back open once more to confirm the existing show-path
(`rmpc-toggle.sh`'s `pgrep -x rmpc` branch) still worked normally.

**Known, deliberate tradeoff**: this makes rmpc's own internal
`Close` action unreachable via Escape specifically for this window
(kitty eats the key before rmpc ever sees it). Not a real loss, though
-- its C-c key entry is bound to the exact same `Close` action in `config.ron`
already, so closing an internal rmpc modal still has a working key,
just Ctrl+C instead of Escape from now on.

## rmpc's theme: recolored by role, not by literal string substitution

Direct feedback: "can we improve the theming of the music player here i
mean use some colors like our status bar and make it more asthetic."
The original theme build (see the mpd/rmpc migration entry below) was a
literal, uniform substitution -- every "blue" in rmpc's own default
theme became the same Mauve, every "yellow" the same Yellow, everywhere
that color name appeared. Technically themed, but the result was almost
monochrome: nearly the whole UI read as Mauve + Yellow, with Red/Green/
Pink only ever showing up in the rarely-seen debug log pane.

Revisited with the actual ask in mind -- richness, and *specifically*
consistency with `waybar/style.css`'s own palette, not just "has hex
colors already". Read waybar's own stylesheet first rather than
guessing which hues it uses where: it deliberately assigns a
*different* color per module (Sapphire = dark mode, Sky = wifi, Peach =
capslock, Teal = numlock, Maroon = the `#pulseaudio` volume module,
Lavender = notifications, a literal dim gray `#6c7086` for every "off"
state) instead of one accent color carrying every role. rmpc's theme
had none of that variety.

Recolored `rmpc/.config/rmpc/themes/catppuccin-mocha.ron` by UI role
this time, picking each hue to match the waybar module it's most
directly analogous to, not at random:

- **Song title** -- had no color at all before, just Bold on the
  default text color, despite being the single most-looked-at line in
  the UI. Now Sky `#89dceb`.
- **Artist** -- was identical Yellow to the `[Playing]` state badge
  right above it. Now Lavender `#b4befe`, genuinely distinct.
- **Volume number/%** -- was generic Mauve. Now Maroon `#eba0ac` --
  not an arbitrary pick, this is *literally* waybar's own `#pulseaudio`
  module color, the most direct "our status bar's colors" match
  available for this exact concept (volume level).
- **Repeat/Random/Consume/Single toggles** -- all four previously
  shared one identical on/off color pair, no way to tell which was
  which by color. Now each gets its own waybar-matched hue when active
  -- Teal (repeat), Peach (random), Sapphire (consume), Lavender
  (single) -- and every *off* state moved from a dimmed Mauve to
  waybar's own literal off-state gray `#6c7086`, matching that
  convention exactly instead of approximating it with a dim modifier
  alone.
- **`level_styles.info`** -- was Mauve, now Sapphire `#74c7ec`, freeing
  Mauve to stay exactly what it already means everywhere else in this
  theme and this desktop: the one "selected/active/interactive" accent
  (`current_item_style`, `borders_style`, `tab_bar.active_style`,
  waybar's own universal hover color) -- diversifying everything else
  deliberately left that single role untouched.
- **Every `#1e1e2e` (Catppuccin's plain "Base") became `#11111b`**
  (modal background, all five `level_styles` backgrounds, and the dark
  contrast-text used against Mauve/Green highlights) -- grepped the
  whole repo first rather than assuming, and confirmed `#11111B` is
  already the one shared dark surface everywhere else in this desktop
  (waybar, mako, wofi, nwg-bar, even sway's own window-border color
  scheme) -- rmpc's theme was the only place still using the lighter
  Base tone for that role.

**Verified live**, not eyeballed: relaunched rmpc through the real
`$mod+Shift+m` keybinding, confirmed its own log showed zero parse
errors for the edited theme (a bad RON edit would either crash rmpc on
launch or silently fall back to defaults -- checked the process was
genuinely still alive with the new file, not assumed), screenshotted
the running window, and pixel-matched specific screen coordinates
against the theme's own target hex values: title, artist, and volume
all came back an *exact* RGB match with zero color distance from what
the theme specifies. The off-state toggle cluster came back a dim,
low-contrast blue-gray in the right position and color family for
`#6c7086` plus the terminal's "Dim" modifier -- not a hex-exact match
on tiny anti-aliased glyph-edge pixels (too fine-grained a target for
this method), but qualitatively confirmed rather than assumed correct.

**Immediate follow-up**: "can't we add some more colors to this tui and
make it more colorfull like our status bar?" The first pass only
touched the playback header and the toggle cluster -- everything else
(file browser rows, table column headers, preview metadata, tab bar,
scrollbar, the elapsed/bitrate line) was still plain, unstyled default
text. Went through every remaining `None`/empty style field in the
theme this time, reusing the same waybar-matched hues plus the two
waybar colors nothing had used yet: Blue `#89b4fa` (waybar's
`#clock.time`) and Rosewater `#f5e0dc` (waybar's wallpaper-refresh
button).

- `symbols.song_style`/`dir_style`/`playlist_style` (the file browser's
  per-row-type marker, all three previously `None`): Sky, Blue,
  Rosewater respectively.
- `browser_song_format`'s Artist/Title fields (actual browser row text,
  previously unstyled): Lavender and Sky -- deliberately matching the
  playback header's own Artist/Title colors, so the browser visually
  ties back to "now playing" instead of being a separate, uncolored
  world.
- `song_table_format`'s column headers (Playlists/Search tabs): Artist
  Lavender, Title Sky, Album Rosewater, Duration Peach. Header row
  only -- left the actual per-song table rows mostly neutral on
  purpose, so a long table of songs stays scannable instead of turning
  into a wall of competing colors row after row.
- `tab_bar.inactive_style` (previously empty/default text): waybar's
  own off-gray `#6c7086` -- a real legibility improvement alongside the
  aesthetic one, since active (filled Mauve) vs. inactive tabs
  previously only differed by which one had a background fill, not by
  any text-color difference too.
- `preview_metadata_group_style` (previously identical Yellow to its
  own `preview_label_style`): Blue, so a label and its value read as
  two distinct things instead of one indistinguishable color.
- `elapsed_and_bitrate` (previously zero color): Green `#a6e3a1`.
- `scrollbar.ends_style` (previously empty): same off-gray as the
  inactive tabs.

Verified the same way as the first pass, not just "compiled without
error": relaunched through the real keybinding, confirmed zero
theme-parse errors and the process still alive, screenshotted, and
pixel-matched. Most of these rendered immediately; `dir_style`'s Blue
specifically only appears on the Directories tab (rmpc's default tab on
launch is Queue), so switched tabs with a real simulated `2` keypress
(`SwitchToTab("Directories")`, per `config.ron`) before screenshotting
that one rather than accepting a zero-match result as evidence it was
broken. Every color checked came back an exact RGB match; the inactive-
tab off-gray came back the right color family across 575 sampled
pixels once a genuine multi-tab screen was on-screen to sample from.

## rmpc's theme, round three: no more background fill on selection, and a real silent-failure bug found

Direct follow-up: "the active item should not get the background
colorf but instead have a rounded colord border. and that quee
directories artists row elements should be colored each differentlly
right also same goes for that normal text as well." Pulled rmpc's own
Rust source directly for this one (`ui/dirstack/mod.rs`,
`ui/panes/queue.rs`, `config/theme/style.rs`) instead of guessing at
what a request like "a rounded border around one row" could even mean
in a ratatui-based TUI.

**No per-item border capability exists, confirmed from the source, not
assumed absent.** `current_item_style` is a plain ratatui `Style`
(`fg`/`bg`/`modifiers` -- confirmed the exact fields on `StyleFile`'s
own struct definition) applied via `.style()` directly on a
`ListItem`/`Row`. There's no border concept for an individual list row
anywhere in the renderer -- borders only ever wrap whole panes. Closest
honest substitute available: dropped `bg` entirely, changed
`current_item_style` to `fg: "#cba6f7"` with `Bold | Underlined` --
no solid fill block, an accent-colored underline standing in for the
outline that genuinely can't be drawn here.

**A real, serious bug found while building that, not just a cosmetic
miss**: first wrote the modifiers as `"Bold, Underlined"`
(comma-separated) -- valid RON syntax, but wrong for how `Modifiers`
actually deserializes. rmpc uses the `bitflags` crate (v2) for that
type, and its serde support parses combined flags in the crate's own
`Flag | Flag` format, not comma-separated -- read the `bitflags!` macro
invocation directly to get the real answer instead of guessing from the
single-modifier examples already in use elsewhere in this file. The
serious part: this didn't just fail to apply that one field -- it
silently took down the **entire config load**, not only the theme.
Found this by comparing `rmpc debuginfo` (run standalone, correctly
resolved every config/theme path) against the actual running instance's
own log: its `Resolved config` dump showed `cache_dir: None` (a
`config.ron`-level setting that has nothing to do with the theme file
at all) and every color rendered as a plain ANSI name (`.yellow()`,
rmpc's own literal built-in default), not any real hex value from this
theme -- meaning one malformed field in the theme file doesn't just
lose its own color, it silently drops the whole `Config` back to
`Default::default()`, no error or warning logged anywhere. Fixed by
using the format the crate actually expects, `"Bold | Underlined"`, and
reconfirmed via the same log comparison: real `Rgb(...)` values back in
`Resolved config`, `cache_dir` back to the configured path.

**Queue/Playlists/Search tables now genuinely colored per column, row
content included, not just headers.** Traced `song_table_format`'s
actual row-rendering path (`queue.rs`'s `as_line_ellipsized`/
`as_line_scrolling` -> `song_ext.rs`'s `as_line`) and confirmed it
*does* apply each column's `prop.style` to the real row text, not only
`label_prop` headers -- so Artist/Title/Album/Duration row content now
matches its own column's header color (Lavender/Sky/Rosewater/Peach)
instead of only Album ever having had an (redundant) explicit color.

**A real, unfixable-via-config limit found for the browser tabs**
(Directories/Artists/Album Artists/Albums): the *other* render path
songs take there (`dirstack/mod.rs`'s `to_list_item`) calls
the Song-typed `Property::as_string` variant, which discards `style` completely
-- confirmed directly in the function body, not inferred. This means
`browser_song_format`'s per-field colors (set in the very first
theming pass, earlier the same evening) were already genuinely inert
dead configuration for real song rows in these tabs, and no theme-level
fix can change that -- only the one-character
type marker before each name
(`symbols.song_style`/`dir_style`/`playlist_style`, already colored
from that first pass) is real there. Left the inert `style:` fields in
the theme file rather than quietly deleting them, with a comment
explaining exactly why, so a future reader (or future me) doesn't
waste time re-discovering the same limitation.

Verified live the same way as every theming pass before it, including
hitting the actual bug live before finding its cause: relaunched,
confirmed via the log comparison above that the config had genuinely
fallen back to full defaults, fixed the modifiers syntax, relaunched
again, confirmed real hex values back in the resolved config,
screenshotted the Queue tab with one real song actually queued (added
it through rmpc's own UI on the real Directories tab, not assumed),
and pixel-matched all four column colors -- exact RGB matches for each.
Ruled out a leftover solid background block on the selected row by
checking row-by-row pixel-count distribution rather than a single
broad scan -- the only full-width Mauve match is the pane's own
horizontal border line, not a fill across the row's own content.

## music-search.py: replacing termusic's broken search with a direct-to-yt-dlp tool

Follow-up to the search diagnosis below: asked directly to build a
replacement rather than just live with the workaround (pasting a raw
YouTube URL) -- "patch up termusic with our own scraping script...
implement our own set of tools that does the same job maybe
differently."

**Checked the obvious existing alternative first, not assumed one
didn't exist**: `ytfzf` (4.1k stars, markets itself as *"without
API"*) -- read its actual source and found its default search path,
`scrape_youtube()`, is a direct alias for `scrape_invidious_search()`.
Same broken dependency, same dead network already confirmed for
termusic. Ruled out rather than adopted.

**Built on the one piece already proven solid**: `yt-dlp`'s own
`ytsearchN:query` search, confirmed completely independent of
Invidious and fast (~2-3s for 10 results with `--flat-playlist`, which
reads only the search-results page itself rather than each video's
full metadata). `mpv`/`ffmpeg` were already installed;
`music-search.py` (new, `scripts/.local/bin/`) wraps this into the same
wofi-search-then-list shape every other picker in this repo already
uses: `$mod+Shift+y` opens a wofi prompt for a query, then a second
wofi list of up to 10 results (title, uploader, duration -- duration
shown deliberately, after accidentally downloading a 3+ hour video once
during testing when a search matched a long-form background-music
stream instead of an actual song), then downloads the picked one as an
mp3 with embedded cover art and metadata into `~/Music`.

**A real, concrete reliability problem found and fixed while building
this, not assumed away**: 2 of 3 real test downloads (different
videos, not livestreams) hit YouTube's *"Sign in to confirm you're not
a bot"* wall using yt-dlp's default extraction path. Confirmed the
standard, documented workaround directly rather than trusting it
blind: `--extractor-args "youtube:player_client=android"` -- the same
exact URLs that failed with the default web client downloaded cleanly
every time with this flag added. Baked into every download this script
does.

**A second real bug caught by testing the actual downloaded state, not
just "did the command exit 0"**: the first version tried to find the
track's own thumbnail (used as the completion notification's icon,
same "use the real fetched image as its own icon" pattern
`fetch_wallpaper.sh` already established) by reconstructing the
expected filename from the search result's raw `title` string --
worked in reasoning, failed on a real download: yt-dlp's own
filesystem sanitization replaced a literal `|` in the title with a
fullwidth `｜` (U+FF5C) when actually writing the file, so the
reconstructed glob matched nothing, silently leaving the thumbnail
file undeleted and falling back to a generic icon instead of the real
one. Fixed by finding the *newest* image file in `~/Music` by mtime
instead of predicting yt-dlp's own naming rules at all -- confirmed via
`makoctl history -j` afterward that the completion notification
correctly references the real thumbnail path, and that the leftover
`.webp` file is gone from `~/Music` post-run.

**Verified fully live, through the actual keybinding and real typed
input** (`ydotool key`/`ydotool type`, not the script run directly):
triggered `$mod+Shift+y`, typed a real query, read the actual search
results back via wofi's own AT-SPI accessibility tree (confirmed real,
relevant titles/uploaders/durations, not placeholder data), picked a
short result, and confirmed the full download completed: `ffprobe`
shows a valid `mp3`-codec audio stream at the expected duration plus an
embedded `png` cover-art stream, and termusic's own startup log
(launched fresh afterward) reports `Finished Scanning "/home/yash/Music"
with 1 created or updated` -- the file is genuinely indexed by
termusic's real library scanner, not just sitting on disk.

termusic's own `s` key is left untouched (still bound to its default,
still technically works if a public Invidious instance ever recovers)
-- `$mod+Shift+y` is just the reliable path now.

## Every popup toggles now, plus termusic: real glass, correct size, and why search fails

Three asks together: every keybinding-launched popup in this repo
should toggle (press the same keybinding again to close it, not just
always open a new one) and close on Escape; termusic specifically needs
an actual glass/transparent background, resized to 60%/50% of the
output; and why doesn't termusic's YouTube search work at all.

### Toggle + Escape, for every popup

**Escape already worked, for the popups where it safely can** -- wofi's
own default keybinding closes its popup on Escape (confirmed nothing in
this repo overrides it), and nwg-bar handles `Key::Escape` internally
too (`gtk.MainQuit()` on release, confirmed straight from its own Go
source) -- neither needed anything added here.

**Toggle needed real work**: `scripts/.local/bin/toggle-popup.sh`, a
generic wrapper every wofi-based popup keybinding and the nwg-bar power
menu now route through (`sway/config`). A marker file per keybinding
(`~/.local/state/popup-toggle/name.pid`) tracks whether *that specific*
popup is the one currently open -- not just "is a wofi process running
somewhere", since every wofi-based picker in this repo shows up as a
bare `wofi` process indistinguishable from any other one by name alone.
Same key while its own popup is open -> close it (same effect as
Escape) and stop. Otherwise -> close whatever *other* popup might be
open first (so switching between two different pickers never stacks
one on top of another), then launch the one requested. Covers the
clipboard-history popup, the emoji picker, the app launcher, the
calculator, every waybar-click-turned-keybinding picker (Wi-Fi,
Bluetooth, Docker, notification history, keybind search), and the power
menu -- ten keybindings in total, all through the one script.

Verified live for two structurally different cases, not just one:
opened the app launcher (a raw `wofi` process) via a simulated keypress,
confirmed it toggled closed on a second press and closed correctly on
Escape too (with the marker file cleaned up either way -- confirmed the
directory ends up genuinely empty after an Escape-close, not just after
the toggle-close path); separately did the same for the power menu
(`nwg-bar`, an entirely different binary, not wofi at all) to confirm
the script generalizes across processes, not just within one tool.

**termusic doesn't route through this script** -- deliberately.
Killing/relaunching its process on every toggle would kill playback too
(it's a real client/server app, not a transient dmenu popup); see below
for what it uses instead.

**A real, honest limitation, not silently skipped**: Escape for
termusic specifically -- making Escape hide termusic *only while it's
the focused window*, without eating Escape for every other application
on the system, isn't something plain sway `bindsym` can safely do.
`bindsym` captures a key combo at the compositor level regardless of
which window is focused; there's no built-in "only when this app_id has
focus" scoping for it (the `[criteria] command` syntax scopes *commands
run via a keybinding*, e.g. `swaymsg '[app_id=...] scratchpad show'`,
not *whether the keybinding itself fires*). Binding a bare `Escape`
globally would have intercepted it in every terminal, editor, and
dialog on the desktop, not just termusic -- a real regression, not a
minor tradeoff. The toggle keybinding (`$mod+Shift+m`, same key hides
it as opens it) already delivers the same practical outcome without
that risk, so that's what termusic actually gets.

### termusic: real glass background

Reported directly: the window looked flat/opaque despite kitty's own
`background_opacity 0.85` (already set globally, `kitty/kitty.conf`,
the same value every other glass surface in this desktop already uses).
**Root cause, confirmed by reading termusic's actual source rather than
assumed**: kitty's `background_opacity` only blends cells using the
terminal's *own* default background -- a TUI application that
explicitly paints a background color into its cells (which termusic's
theme did: `primary.background = "#1e1e2e"`, a literal opaque hex) gets
drawn at full opacity regardless of the window's own setting. This is a
real, known kitty+TUI-app interaction, not a bug in either tool
individually.

Confirmed termusic has a first-class way around this before assuming
one didn't exist: its theme system supports a `"native"` value
(`ThemeColor::Native`) that resolves straight to `ratatui::Color::Reset`
for `Background` specifically (`ColorTermusic::Background => Color::Reset`,
confirmed reading `styles.rs` directly) -- "don't paint anything
explicit here, let whatever's already there show through" instead of a
literal hex. Every panel's own `background_color` in `tui.toml`
(library/playlist/lyric/progress/etc.) already referenced this same
field symbolically (`background_color = "Background"`, not a hardcoded
color of its own), so changing the one value
(`[theme.primary] background = "native"`) cascaded correctly to the
entire UI in a single edit, confirmed by reading the generated config
rather than guessing it would.

Verified live, not just "should now blend": screenshotted the actual
running window before and after -- 0% of its pixels are the old literal
Mocha hex now (previously the vast majority were), confirming the
explicit paint is genuinely gone. The resulting colors read very dark,
which looked suspicious at first -- cross-checked directly by hiding
the window and screenshotting the *exact same screen region* with
nothing but wallpaper in it: also very dark, confirming this is a
correctly-blended, coincidentally-dark patch of the current wallpaper
under an 85%-opacity dark terminal background, not a failure to blend
at all (the math checks out: kitty's own near-black default background
at 0.85 opacity dominates the blend regardless of what's behind it,
same as it does for every other glass surface in this setup).

### termusic: resized to 60%/50%, toggled via scratchpad

`for_window [app_id="^termusic$"]` now sizes it to `1152x540` (60%
width / 50% height of this machine's actual `1920x1080` output,
computed directly rather than guessed, and left as fixed pixels rather
than `ppt` -- sway's own docs are ambiguous on whether percentage units
apply to *floating* containers the way they unambiguously do for tiled
ones, not worth the risk of a silently-wrong size for one window).

Toggling uses sway's scratchpad (`scripts/.local/bin/termusic-toggle.sh`),
not the same kill-and-relaunch `toggle-popup.sh` every other popup uses
-- deliberately, so playback never stops while the window is hidden.
First launch: no window exists yet, so it starts fresh and the
`for_window` rule (floating + sized + centered + moved into the
scratchpad + shown immediately, all in one rule) makes it appear
correctly. Every press after that: `swaymsg '[app_id="^termusic$"]
scratchpad show'` alone -- confirmed directly, not assumed from sway's
own slightly ambiguous docs ("cycles through windows... showing and
hiding them"), that calling this on a window already shown from the
scratchpad genuinely hides it again rather than being a no-op, by
toggling it twice and checking which pseudo-workspace (`__i3_scratch`
when hidden, the real workspace name when shown) the window actually
sits on after each call. Also confirmed directly that hiding it this
way never touches the underlying process at all -- the same termusic
client and `termusic-server` PIDs stay up the entire time across a
hide/show cycle, and the server's own log shows no disconnect/reconnect
during it.

A real, unrelated bug caught while building this: the first version of
`termusic-toggle.sh` launched kitty as a plain backgrounded shell job
(`kitty ... &`) -- inheriting this script's own stdout/stderr meant
whatever invoked the script (sway's `exec`, a test shell) could hang
waiting for those file descriptors to close for as long as kitty kept
running, instead of returning immediately the way a background launch
should. Fixed with `setsid` plus redirected stdio, the same pattern
already used for every other backgrounded GUI launch verified this
session.

### Why YouTube search fails: a real, external problem, not this setup

**Confirmed directly, not assumed, that this isn't a local network or
config problem first**: `yt-dlp` itself, called directly, resolves
DNS, reaches `youtube.com`, and returns real search results with zero
issues. So the network, DNS, and `yt-dlp` itself are all fine -- the
problem is specific to termusic's own search *mechanism*.

**Root cause, found in termusic's own TUI log
(`/tmp/termusic-tui.log`)**: `Youtube search fail: Something is wrong
with your connection or all 7 invidious servers are down.` termusic's
free-text search (the `s` popup) does **not** use `yt-dlp` for
searching at all -- only for the download step, once a result is
already picked. Searching goes through the public
[Invidious](https://invidious.io) instance network instead (confirmed
reading `lib/src/invidious.rs` directly): it tries to fetch a live
instance list from `api.invidious.io`, falls back to five hardcoded
instance URLs if that fails, and needs at least one instance's
`/api/v1/search` endpoint to actually respond correctly.

**Tested every candidate instance's actual search endpoint directly,
not just whether the domain responds to a bare request** -- three of
termusic's five hardcoded fallbacks answered a plain request fine but
failed the specific `/api/v1/search` call for three different concrete
reasons: `inv.nadeko.net` returns `403 Endpoint disabled` (search
explicitly turned off by that instance's own operator), 
`invidious.nerdvpn.de` returns `401 Authorization Required`, `yewtu.be`
serves an anti-bot JavaScript challenge page instead of JSON (blocks
any plain HTTP client, not just termusic). The other two hardcoded
fallbacks (`yt.artemislena.eu`, `y.com.sb`) are simply unreachable.
Checked the live, currently-maintained instance directory itself too
(`api.invidious.io/instances.json`) rather than assuming termusic's
five were just unlucky picks: **zero of the 11 instances it currently
lists have their public API enabled at all**. This is Invidious's
entire public network in its current state, not a handful of bad server
picks -- something termusic itself has no control over, and something a
newer termusic version wouldn't fix either (checked the current
upstream `master` branch changelog: still Invidious-based, no
alternative search backend has been added).

**The actual, working path around it, right now**: paste a direct
YouTube video URL into the same `s` popup instead of typing a text
query -- that skips the broken Invidious search step entirely and goes
straight to the `yt-dlp` download path, which is already confirmed
fully working. Practically: find the song elsewhere (a browser search),
copy its YouTube URL, paste it into termusic. Not the pure "type a song
name and go" experience originally hoped for, but a real, working
mitigation rather than a dead end -- and an honest limitation to flag
rather than something to paper over.

## termusic: a CLI music player with no local library and no Premium subscription

Asked for a "beautiful CLI" music player, explicit constraints: no
local music library to start from, no Spotify or YouTube Premium
subscription to lean on -- it needs to actually fetch music from the
cloud itself.

**Picked termusic specifically because it says the quiet part out
loud** in its own README: *"You can download from YouTube, NetEase,
Migu and KuGou for free. No need to register for monthly paid
memberships."* Ruled out the other well-known "beautiful TUI music
player" options directly against that constraint rather than assuming:
`spotify-player`/`ncspot` both require Spotify Premium to actually play
anything (a restriction Spotify itself enforces on third-party
Connect/librespot clients, not something either project can route
around); `rmpc`/`cmus` are both local-library-only, no built-in way to
pull anything from the cloud at all. termusic was the only candidate
that actually solves "flashy *and* no subscription *and* no existing
library" simultaneously.

**Confirmed the actual cloud-fetch mechanic from its own source before
relying on it**, not assumed from the README's marketing copy alone:
`s` (default `library_keys.youtube_search` binding) opens a "Download
url or search:" popup -- type a song/artist name, pick a result, it
downloads the audio via `yt-dlp` straight into `~/Music`, adds it to
the playlist, and plays. Works from a genuinely empty `~/Music` --
nothing needs to exist beforehand, the library builds itself purely
from searching.

**Directly in Arch's official `extra` repo** (`packages/pacman.txt`) --
no AUR, no building a Rust project from source, which its own MSRV
requirement (`1.90.0`) would have made a real wait. `yt-dlp` added
alongside it (the actual thing that lets it reach YouTube at all);
`ffmpeg`/`kitty` were already installed.

**A real version mismatch, found by checking rather than assuming
current-upstream matches the installed package**: upstream `master`
ships an official `Catppuccin-Mocha.yml` theme in its own source tree
(exact ANSI-color match to the canonical Catppuccin terminal spec, not
a close approximation) -- but the Arch package here is `0.13.2-1`,
built before that theme existed upstream. Confirmed directly: launched
termusic once, let it create its own `~/.config/termusic/themes/`
(214 bundled files), and it genuinely wasn't among them. Copied the
file in by hand from upstream's source tree instead of trusting the
installed version to already have it.

**Theme selection baked in, not left as a manual first-run step** --
avoided guessing the TOML shape of a nested Rust config struct blind
(a real risk this session has been burned by more than once elsewhere,
e.g. waybar's broken `format-icons` threshold form): launched termusic
with no config at all first, let it generate its own real defaults, and
read the actual resulting `tui.toml`'s `[theme]`/`[theme.primary]`/
`[theme.cursor]`/`[theme.normal]`/`[theme.bright]` shape directly before
writing anything, rather than inferring it from the Rust source's field
names alone. Wrote the Catppuccin Mocha hex values into that exact
confirmed shape.

**Config vs. state, same line this repo draws everywhere else**: only
`tui.toml`, `server.toml`, and the one theme file are stowed into this
repo -- `~/.config/termusic/` also holds `data.db`/`library2.db`/
`playlist.log` (a real SQLite library index and playback queue, not
configuration) and termusic's own 213 other bundled theme files, all
deliberately left as real local files, not symlinked in, the same
config-vs-state boundary already established for
`~/.local/state/notification-mode/` and `~/.local/state/caffeine/`.
This works cleanly because `~/.config/termusic/` already existed as a
real directory (termusic creates it itself on first run) *before* this
package was ever stowed -- confirmed with `stow -n -v` first that GNU
Stow's own tree-folding behavior symlinks the three individual files in
rather than replacing the whole directory with one symlink, which would
have pulled the runtime databases into version control right along with
them.

**Launch**: `$mod+Shift+m` opens it in its own floating kitty window
(`kitty --class termusic -e termusic`, sized/centered via
`for_window [app_id="^termusic$"]` in `sway/config`) -- floating on
purpose, not tiled, the same reasoning as every other "glance at it,
dismiss it" tool in this setup rather than something that permanently
claims a tiling slot.

**Verified live end to end, not just "should work"**: triggered the
real `$mod+Shift+m` keybinding via a simulated keypress (not the launch
command run manually), confirmed via `swaymsg -t get_tree` that a
900x700 floating window opened at the expected centered position, and
screenshotted the actual running window -- 88.6% of its pixels are the
exact Catppuccin Mocha background hex (`#1e1e2e`), confirming the theme
is genuinely active in the real keybinding-launched instance, not just
a separately-tested one.

## Power menu, polish pass: label rename, thinner icons, real icon/label gap

Three small, concrete asks together: rename "Shutdown" to "Power off",
make the icons thinner, and add real space between icon and label --
nwg-bar stacks them with zero gap of its own between (its own source:
`SetImagePosition(gtk.POS_TOP)`, nothing else).

- `bar.json`'s label changed directly, no icon/exec change needed.
- Icon stroke-width dropped from 2 to 1.5 across all five (icons/*.svg)
  -- same Lucide path data as the previous pass, just a thinner line.
- Icon size dropped from nwg-bar's own default (48px, undeclared until
  now) to an explicit `-i 40` on both places nwg-bar gets launched
  (waybar's `custom/power` on-click, `sway/config`'s `$mod+Shift+p`) --
  the icons read as slightly oversized/cramped against the button's own
  padding at the default size.
- The actual gap: `image { margin-bottom: 10px; }` in `style.css` --
  `image` is the element sitting directly above the label in nwg-bar's
  own POS_TOP stack, so a bottom margin on it *is* the icon-label gap.
  No dedicated "icon" or "label" CSS node exists to target more
  specifically than that (confirmed from nwg-bar's own source -- it
  just calls `button.SetImage()`/`button.SetLabel()` and lets GTK's
  default button-content box handle layout).

Verified live, measuring the actual before/after gap rather than
assuming the margin took effect: read the padlock icon's own rendered
pixels back as ASCII art before and after -- icon bottom edge to label
top edge went from roughly 9px to roughly 19px, a real, measurable
change, not just a CSS value that might not have applied. Confirmed via
nwg-bar's own AT-SPI accessibility tree that the fifth button now
reports itself as "Power off", not "Shutdown". Reconfirmed the five
per-action border colors from every earlier pass were unaffected.

## Power menu, third icon pass: lean stroke icons, all five in one family

Direct feedback right after the Adwaita swap below: "older once were
better than this. i want lean icons just like the older once but just
different." The Adwaita set fixed *meaning* (a real moon instead of an
ambiguous ring) but lost the *look* -- solid, bold shapes where the
originals were thin single-stroke outlines. The actual ask all along was
both at once: keep the lean look, fix the shapes that weren't meaningful.

Landed on [Lucide](https://lucide.dev) -- a modern line-icon set (24x24
grid, consistent 2px stroke, round caps/joins, no fill) that's exactly
the "lean" language the original nwg-bar icons were reaching for, just
executed properly and with genuinely distinct shapes per action. Found
it already vendored locally as an npm dependency in an unrelated project
on this machine (`lucide-react` under
`~/Codes/claude-remote-main/client/node_modules/`) -- no network fetch
needed, the exact path data for `lock`, `log-out`, `moon`, `rotate-cw`,
and `power` came straight out of that package's own per-icon source
files. All five rebuilt as plain standalone SVGs from that data, same
stroke weight and style across the board -- one coherent family this
time, not a patchwork of old-style-plus-one-new-icon (the previous
pass's own real shortcoming) or a style mismatch against a set that
used to be lean (the Adwaita pass's shortcoming).

Lucide's own default is `stroke="currentColor"` -- swapped for hardcoded
`#CDD6F4` before use, the exact same reasoning applied to every other
icon fix in this repo: these load as raw files via an absolute path, not
through GTK's icon-theme resolution, so `currentColor` has no reliable
context here. `power` specifically is functionally identical to what
Shutdown already had (ring + vertical line, the real ISO standby
symbol) -- swapped anyway, for stroke-weight consistency with the other
four rather than leaving one differently-drawn icon in an otherwise
uniform set.

Verified live the same way as every icon pass this session: launched
`nwg-bar` directly, read all five icons' actual rendered pixels back as
ASCII art -- a genuinely hollow padlock, a door-plus-arrow logout, a
thin crescent moon (finally, distinctly *not* a ring), a circular
refresh arrow, and the power symbol, all at the same visual weight.
Reconfirmed the five per-action border colors from the earlier pass
were unaffected (386-795 matching pixels each, same range as before).

## Power menu: better icon shapes, four of five swapped for Adwaita's

Reported directly, with a specific example: Suspend rendered as "a
circle with a vertical rod in the middle" -- not a meaningful shape --
and asked for better icons generally, not just that one.

Checked Papirus's own `system-suspend-symbolic` as the obvious first
candidate and rejected it -- it's the *same* ring-plus-horizontal-dash
concept already in use, just a slightly different rendering of the
identical idea, so swapping to it wouldn't have actually addressed the
complaint. Went with a genuinely different, unambiguous concept instead:
a crescent moon (Papirus's own `weather-clear-night-symbolic` shape,
recolored) -- the universal "sleep" symbol, immediately readable in a
way an abstract ring never was.

While at it, swapped Lock/Logout/Reboot to Adwaita's own symbolic icon
set too (GNOME's, clean and widely recognized) rather than leaving a
patchwork of nwg-bar's original minimal shapes next to one new moon --
one coherent icon family reads better than a mismatched set, and this
was explicitly asked for "better icons for those buttons" (plural, not
just Suspend). Shutdown untouched -- it was already correct from the
previous pass (the real ISO power/standby symbol), no reason to change
what wasn't broken.

Every Adwaita source icon ships with a hardcoded fill meant for *light*
GNOME toolbars (`#2e3436`) -- the exact same "icon designed for the
wrong background" issue already found and fixed for mako's own
notification icons earlier this session, not a new class of problem.
Recolored to `#CDD6F4` (Clean Silver, this bar's own text color) before
use. Full source/shape mapping and reasoning in `icons/README.md`.

Verified live, not assumed correct from reading the source SVGs alone:
launched `nwg-bar` directly and read every one of the five icons' actual
rendered pixels back as ASCII art -- a real padlock (Lock), a clear exit
arrow (Logout), an unambiguous crescent moon (Suspend), a circular
refresh arrow (Reboot), confirmed distinct from each other and each
individually recognizable at the size they actually render at, not just
plausible-looking in isolation. Confirmed the five per-action border
colors from the previous pass were unaffected -- 386-780 matching pixels
each, same range as before this change.

## Power menu: keybinding, and verifying Tab navigation without ever pressing Enter

Asked for a keybinding to open the power menu (same gap every other
waybar-click-only picker in this repo already had fixed --
`$mod+Shift+p`, matching the established `$mod+Shift+letter`
convention for exactly this class of fix) and for Tab to move between
its buttons.

**A real constraint shaped how this got tested**: every single action in
this menu -- Lock, Logout, Suspend, Reboot, Shutdown -- is disruptive or
outright hard to reverse. Pressing Enter to check "did Tab land on the
right button" risks actually locking, logging out, suspending,
rebooting, or shutting down the remote session being worked in, which
this whole session has held as a hard line to never do for testing
purposes. Screenshotting for a visible focus indicator wasn't reliable
either at first -- zero pixels differed before Tab was actually styled
for `:focus` (below), which would have read as "Tab doesn't work" when
it actually did, just invisibly.

Solved with something genuinely safe and precise instead: nwg-bar
already registers itself on the AT-SPI accessibility bus (confirmed
directly -- `Atspi.get_desktop(0)` lists it alongside waybar and the
system tray applets). Queried its own accessibility tree read-only after
each simulated Tab/Shift+Tab press and asked which button reports
itself `FOCUSED` -- no risk of activating anything, this is the same
mechanism screen readers use, purely observational. Confirmed the full
cycle, both directions, with wraparound: Lock -> Logout -> Suspend ->
Reboot -> Shutdown -> (wraps) -> Lock forward, and the same in reverse
with Shift+Tab. This works because nwg-bar requests exclusive layer-
shell keyboard focus itself (`LAYER_SHELL_KEYBOARD_MODE_EXCLUSIVE`,
confirmed straight from its own Go source) and real GtkButtons in a
GtkBox get Tab-chain navigation from GTK for free on top of that --
nothing this repo had to build, just verify.

**Found a real gap while verifying, not something asked for directly**:
focus was genuinely moving the whole time, but nothing was styled to
show it -- confirmed by screenshotting before/after a Tab press and
finding the card region byte-for-byte identical. Fixed by giving
`:focus` the exact same treatment as `:hover` on every per-action rule
(same `nth-child` selectors, `style.css`) -- keyboard nav and mouse
hover now read as the same "this one's about to activate" state, which
is also just the more honest model of what's actually true. Re-verified
after the style fix: the same before/after screenshot diff that read 0
now reads 35936 differing pixels for a single Tab press, and AT-SPI
confirms the button that's actually focused matches which one visibly
glows.

## Power menu, corrected: color moved to the pill, glass+border on every button, and a real CSS bug

Direct, blunt feedback right after the entry below: the icon-recoloring
approach was wrong ("by colors i don't mean those icons"), and the card
itself was missing the glass background/border it was supposed to
already have on every button, not just the outer frame.

**Color, moved to the right layer**: reverted every icon back to plain
(stock `fill:none`, matching nwg-bar's own upstream appearance -- see
`icons/README.md`). Per-action color now lives on the button itself,
mirroring exactly how waybar colors its own modules -- a colored border
at low opacity, brighter plus a soft glow on hover, the same two-
strength pattern waybar's own hover states already use everywhere else.
nwg-bar gives buttons no individual CSS name/class (confirmed from its
own source), so the five per-action rules key off `:nth-child(N)`
against `bar.json`'s own fixed action order instead of a name selector.

**Glass + border on every button, not just on hover**: previously
`button { background: none; border: none; }` until hover added them --
technically the outer card *did* have its own glass+border the whole
time, but each individual button had no chrome of its own at rest,
which is almost certainly what read as "no glass, no border" even
though the outer frame was there. Gave every button waybar's own exact
module-pill formula (`rgba(17,17,27,...)` fill, 16px radius, a subtle
low-opacity Mauve-family hairline border) as its resting state, not just
its hover state -- "follow the theme of the status bar" taken literally,
copying the actual formula rather than a vague gesture at "glassy".

**A real bug found in the process, not just a design miss**: the very
first attempt at this fix (which added `:nth-child` selectors and new
per-action comments) silently failed to apply *at all* -- `nwg-bar`'s
own log said outright: `style.css file erroneous or not found, using
GTK styling`, meaning every single change in that pass rendered as bare
default GTK chrome instead, worse than before either fix. Diagnosed
precisely with GTK's own `Gtk.CssProvider` `parsing-error` signal
(connected to it directly from Python rather than guessing) --
`style.css:14:38 '/*' in comment block`. The cause: a comment's own
prose mentioned `icons/*.svg`, and CSS comments can't nest -- the literal
`/*` inside that path broke out of the comment early and confused
everything after it. Fixed by rewording the one line; re-checked with
the same `parsing-error` signal afterward and got zero errors before
trusting it further. Worth remembering for any future CSS comment in
this repo: never write a literal `/*` inside prose, even referring to a
glob pattern -- GTK's CSS parser (and CSS in general) has no escape for
it inside a comment.

Verified live end to end, not just "parses now": launched `nwg-bar`
directly, confirmed the log now says `Using style: ...` instead of the
erroneous-fallback message, screenshotted the real card, confirmed zero
pixels matching any of the old icon-fill colors (icons genuinely back to
plain), and found substantial, distinct pixel counts for all five
button-border colors at their expected low-opacity blend within the
card region. Read the Shutdown icon's own glyph back as ASCII art too --
a clean ring outline with no fill behind it, matching stock exactly.

## Power menu icons: invisible colored circles, no per-action distinction

Asked for the power-menu icons (nwg-bar, `custom/power`'s waybar
on-click) to actually show meaningful, colored icons -- specifically
that Shutdown should look like an actual power button.

**Root cause, found by reading the actual SVG, not assuming a stock icon
pack just works**: nwg-bar's own stock icons
(`/usr/share/nwg-bar/images/*.svg`) each have a colored circle
(`fill="#c2352a"` etc.) with an inline `style="fill:none;fill-opacity:1"`
on the *same element* -- CSS style always wins over a plain presentation
attribute, so the circle's color was silently disabled in every single
one of them. Every action rendered as the same flat white ring glyph
with nothing behind it, regardless of theme -- not "small" or "wrong
shape", genuinely invisible color. Separately, Suspend and Shutdown
shipped the exact same red (`#c2352a`) even with the fill working, so
there'd have been no color distinction between a soft/reversible action
and a final one anyway.

nwg-bar gives buttons no individual CSS name/class to target per action
(confirmed from its own source, already noted in `style.css` from the
switch away from wofi for this menu) -- so per-action color can't live
at the CSS layer here the way every other module in this bar does it.
Made local copies of the five icons actually used
(`nwg-bar/.config/nwg-bar/icons/`, `bar.json` repointed at them instead
of the system path) rather than editing package files directly, removed
the `fill:none` override, and recolored each to this desktop's own
Catppuccin Mocha palette instead of the stock pack's arbitrary colors --
full mapping and reasoning in that directory's own `README.md`. Glyph
shapes were already correct and untouched -- Shutdown in particular is
already the real ISO power/standby symbol, just needed its color back.

Verified live: launched `nwg-bar` directly, screenshotted the real card,
and read the pixels back as ASCII art for both Shutdown and Lock --
confirmed a solid colored circle with the white glyph cleanly cut out of
the middle for each, the same ground-truth method the volume icon saga
(below) established as the only one that's actually caught every real
issue this session, rather than the color-tolerance sampling that missed
problems twice in a row there.

## Volume icon, third pass: dropped the glow -- the real fix didn't need it

Asked directly, after the format-icons bug was fixed and the icon was
genuinely rendering again: why does it have a glow, make it normal. Fair
question -- the `text-shadow` on `#pulseaudio` was added specifically to
make an *invisible* icon more noticeable, back when the actual problem
was believed to be "too small" rather than "not rendering at all". Once
the real cause turned out to be waybar's broken `format-icons`
threshold-object form (previous entry) and the fix moved to
`volume_osd.sh` setting real PulseAudio mute at 0%, the glow's original
justification was already gone -- it was solving a problem ("small/hard
to notice") that had already been fully addressed by the icon simply
rendering correctly again. Removed it; `#pulseaudio` is back to a plain
resting color like every other module in this bar, nothing left to
explain away.

Verified live with the same ASCII-dump method as the previous two
entries (not the color-tolerance sampling that misled the earlier
passes on this exact feature): the icon at 80% renders as a tighter,
crisper glyph shape with the shadow gone, still clearly present.

## Volume icon, second correction: waybar's threshold-object format-icons is broken here; a real bug, not a config mistake

Reported again, still after the text-shadow fix: "only when its muted
does it show the icon" -- the size/glow problem was actually fixed, but
the icon was invisible at every *regular* volume level the whole time,
not just small. My two previous verification passes on this exact
feature (color-tolerance pixel matching, both times) missed it -- worth
being honest about a third time getting this feature's diagnosis wrong
before it landed correctly.

**Stopped trusting color-heuristic sampling entirely this time** and
switched to a fundamentally more reliable method: dump the actual
screenshot region as raw ASCII art (luminance-thresholded, `#` for
"clearly brighter than background", `.` otherwise) and read the glyph
shapes directly, the way a person would look at the bar itself, instead
of pre-supposing a hue to filter for. This immediately showed the real
picture: at 80% volume, the bar rendered `<backlight icon>  80%` with
*nothing* between the two spaces and the digits -- no icon at all, not
a small one. Toggling actual mute, the exact same technique showed a
genuinely new glyph appearing in that same gap. So the earlier
"verified 20x9px glow at every level" and "consistent 12x9px footprint"
claims from the previous two entries were both artifacts of the sampling
method itself -- likely picking up backlight's own nearby icon or
antialiasing noise that happened to pass a Maroon-ish color filter, not
the pulseaudio icon actually rendering. A hard lesson in this session
about verification methods that can *look* rigorous (measuring exact
pixel counts and bounding boxes) while still being wrong at the premise
level (matching the wrong thing entirely).

**Root cause, isolated properly this time**: `format-icons`'s
threshold-object form (`{"icon": ..., "max": N}`, added specifically to
give 0% its own icon separate from "just quiet") is real and documented
-- straight from waybar's own source, `src/ALabel.cpp`. Reverted it back
to the plain 3-item array with nothing else changed, re-ran the same
ASCII-dump test: the icon reappeared immediately, correctly, at every
level. Re-applied the threshold-object form alone, nothing else changed:
gone again. This isolates it cleanly -- the threshold-object array
genuinely does not render an icon for the pulseaudio module's regular
(non-muted) format string in this waybar build (v0.15.0), while the
exact same array shape and the exact same source code path works for
every other reported case in this repo (e.g. `format-muted`, which
never used `format-icons` at all -- it's a fully hardcoded string, which
is *why* the muted case kept working the whole time and looked like
proof the feature worked). Concluded this is a genuine bug or version-
specific incompatibility in waybar itself, not a JSON mistake -- filed
under "don't rely on this" rather than fought further blind.

**Fix, moved to where it can actually be guaranteed to work**: instead
of trying to make waybar's icon selection distinguish 0% from "just
quiet" (the broken path), made 0% and *actual* mute the same real
PulseAudio state instead. `volume_osd.sh`'s `adjust_volume()` now sets
the real mute flag whenever a scroll/keypress lands exactly on 0%, and
clears it the moment volume moves back above 0% -- so `format-muted`
(the one path already proven correct this whole time) picks it up
naturally. This also happens to be a more honest model of reality: 0%
and muted really are the same silence to the ear, so making them the
same underlying PulseAudio state is more correct than trying to fake
the same *look* via two independent, divergent code paths.

**Verified with the ASCII-dump method throughout, not the old color
sampling**: 15/50/90% each render a real, distinct icon shape again.
Scrolling down to 0% via the actual `volume_osd.sh -5%` path (not raw
`pactl`) confirmed `Mute: yes` at the PulseAudio level and the expected
new glyph + "Muted" text appearing in the bar. Scrolling back up
confirmed `Mute: no` and the normal icon+percent display returning.

**One known, accepted gap**: this only auto-mutes when 0% is reached
through `volume_osd.sh` itself (the OSD script all of this repo's own
scroll/keybinding paths already go through). Setting volume to exactly
0% through some other tool entirely (`pavucontrol`'s own slider, a
different script) bypasses this and would still show the old "just
quiet" look rather than "muted" -- an accepted gap matching this
session's general practice of solving the primary, actually-used
interaction path robustly rather than chasing every possible external
tool that could also touch the same PulseAudio state.

## Volume icon, correction: the span-size fix broke rendering; text-shadow is what actually worked

Reported right after the entry below: the volume icon wasn't visible at
all anymore, and the muted icon + "Muted" text weren't on the same
line. Both true, and both caused by the fix in the entry below --
recorded here rather than editing that entry in place, since being
honest about a real regression (and the reasoning that led to it) is
worth keeping visible, not quietly erasing.

**What actually went wrong, found by isolating variables one at a
time rather than guessing**: the previous fix wrapped just `{icon}` in
its own inline Pango span (`<span size='16384'>{icon}</span>`) to grow
the icon without touching the percent text next to it. Reverted that
first and re-tested with plain format strings (icon still small, but
present and correctly aligned) -- confirming the *icon-only span* was
the actual cause, not the separate `format-icons` threshold-object
restructuring done alongside it (that part checked out fine on its own).
Then tried the more conventional alternative, a uniform `font-size` bump
on the whole `#pulseaudio` module (same size for icon and text, avoiding
a mixed-size line entirely) -- and hit a second, different, genuinely
strange failure: at 15px, the three volume-level glyphs (low/medium/
high) stopped rendering completely (0 matching pixels, confirmed via
screenshot), while the *mute* glyph and the plain percent digits kept
rendering fine at the exact same size. Reproducible, isolated by testing
font-size on its own with nothing else changed -- a real quirk in how
this specific Nerd Font's icon glyphs rasterize via this Pango/Cairo
stack at that size, not something worth chasing further blind with only
pixel-sampling as a diagnostic (no way to actually *look* at the render
the way a person can -- worth stating plainly rather than continuing to
guess at magic numbers).

Tried `font-weight: 700` next, since this exact stylesheet already
proved it safe elsewhere (workspace numbers) -- confirmed it changed
nothing at all for these specific glyphs (no visible difference,
but also no breakage) -- likely a single-weight icon font with no bold
variant to fall back to differently. Landed on `text-shadow` instead --
the same paint-only technique this file already used successfully once
before for "make something louder without touching layout"
(`#custom-capslock.locked`'s own glow) -- doesn't change box size or
font rendering at all, just adds a soft Maroon halo around whatever
already rendered. Verified this one properly: measured the icon's
visible footprint by color-matching for a Maroon-ish hue (not exact-color
match this time, since a soft glow blends toward the background at its
edges) rather than trusting a loose "anything non-background" check,
which the first pass at this measurement wrongly picked up on unrelated
neighboring modules (backlight's own Yellow icon bleeding into the same
crop region) before being narrowed down. Result: a consistent ~12x9px
glow footprint at every volume level (versus ~4-5px bare before), icon
and "Muted"/percent text sitting on the same y-range (15-25 and 16-24
respectively -- properly aligned, unlike the broken span version), and
the glyphs render at all, which they didn't at 15px.

## Volume icon: too small to notice, and 0% didn't look muted

Asked two things, framed as one report: at 0% volume (not the actual
PulseAudio mute flag, just the slider at zero) the icon didn't change to
look muted, and separately the icon in general is hard to notice at low
volumes -- asked for my actual design opinion on the first one rather
than just doing whatever was asked, and to fix icon size so it stays
"consistent and visible" rather than wobbling per level.

**Design opinion, given directly rather than silently implementing
either way**: yes, 0% should look the same as an actual mute. There's no
audible difference between "volume slider at zero" and "muted" -- both
are silent -- so showing the "just quiet" icon at 0% instead of a
muted-looking one is actively misleading, not a neutral design choice.
Fixed accordingly.

**Root cause of "hard to notice", found by measuring real pixels, not
guessed**: cropped a live screenshot down to just the icon glyph and
measured its exact bounding box at three volume levels -- ~4x5px of
actual ink, at every level, regardless of which of the three glyphs was
showing. That's tiny at this bar's 12px base font-size; the icon reading
as "too small" wasn't really about *which* volume level, the whole glyph
set is just small there.

**0% fix**: waybar's `format-icons` isn't limited to the evenly-bucketed
plain array this repo had been using (`["low","med","high"]`, which
divides 0-100 into three equal thirds -- 0% and 20% landed in the exact
same bucket, both showing the "low" glyph). Confirmed directly from
waybar's own source (`src/ALabel.cpp`, `getIcon()`) that `format-icons`
also accepts an array of `{"icon": ..., "max": N}` threshold objects,
checked in order, first match wins -- gives an exact, standalone 0%
bucket. Reuses `format-muted`'s own existing crossed-out glyph
(U+F075F, already in the pre-existing config, confirmed present in the
installed Nerd Font via `fc-list` before reusing it) rather than
inventing a fourth new one -- 0%-unmuted and actually-muted are the same
*experience* for the user, so they should be the same *icon*, not two
different ones
that both mean "silent."

**Size fix**: wrapped `{icon}` in its own Pango span
(`<span size='16384'>{icon}</span>`) directly inside the `format`
string, sizing *only* the icon, not the percent-text next to it --
Pango spans with attributes already confirmed working in this exact
waybar version elsewhere in this repo (`docker-status.sh`'s own
`<span color=...>` usage), so this wasn't a new, unverified mechanism.
Deliberately **not** a CSS `font-size` change, and deliberately
**not** state-conditional -- this exact repo already hit a real failure
mode doing that once before: bumping `font-size` on
`#custom-capslock.locked` (a *dynamic* state that toggles at runtime)
visibly popped the whole bar taller the instant the state activated,
since waybar's `height` config doesn't hard-clip an over-tall label
(documented in that rule's own comment in `style.css`). A span size
baked directly into the static `format` template has neither problem --
it's the same size on every single render, from waybar's very first
frame onward, so there's no "before" state to jump from and nothing
ever pops.

**Verified live**, not just reasoned about: restarted waybar for real
this time (the previous entry above already found `SIGUSR2` doesn't
reload anything in this config) and measured the icon's own bounding
box again at 15/50/90% -- now a consistent x=92-111, y=16-24 (20x9px)
at every level, identical footprint regardless of which glyph is
showing, versus ~4x5px before. Confirmed 0% (unmuted) renders a visibly
different, narrower glyph in the same y-range -- the reused mute icon,
not the "low" one. Confirmed the true-mute case (`pactl set-sink-mute`)
still renders correctly too. Confirmed no bar-height pop from the
static span size, screenshotting the bar's own background extent before
and after the restart.

## Workspace indicator, follow-up: occupied numbers were too dim, and a real waybar-reload gap

Reported right after the occupancy feature below: the occupied-but-
unfocused number (translucent Red, 0.7 alpha) was "slightly hard to
notice". Also clarified the intended signal split more precisely: the
number color should say "there's a window here, or this is where I am"
-- deliberately not distinguishing between those two on its own -- and
the underline should be the *only* thing that confirms "this one
specifically is current". That's a cleaner design than graduated
color intensity was: bumped the occupied rule's color from
`rgba(243, 139, 168, 0.7)` to solid `#F38BA8`, identical to `.focused`.
The two states now differ only in font-weight (600 vs 800, a secondary,
non-load-bearing cue) and the underline, which stays exclusively on
`.focused`.

**A real gap found while re-verifying this, not part of what was
reported but worth recording**: re-checked the fix by sending
`pkill -SIGUSR2 waybar` and screenshotting, same as the first pass on
this feature -- and initially got ambiguous, inconsistent-looking pixel
counts. Read waybar's own source (`src/main.cpp`) to check what SIGUSR2
actually does by default: nothing, unless the bar config sets its own
`on-sigusr2-action` (ours doesn't) -- it's a no-op signal here, not a
style/config reload trigger. waybar also doesn't appear to file-watch
its own CSS for hot-reload (checked `client.cpp`'s `setupCss`, only
called at startup). So the *first* pass's "live verification" earlier
this session may well have been screenshotting a stale render by
coincidence of the colors happening to look plausible, not an actually-
confirmed reload -- worth being honest about here rather than letting it
stand uncorrected. Fixed properly this time by actually restarting
waybar (`pkill` the old process, launch a fresh detached one via
`setsid waybar & disown`, since `sway/config`'s `exec waybar` isn't a
supervised/auto-restarting exec) rather than trusting a signal with an
unconfirmed effect. **Lesson for next time touching waybar's CSS**:
restart the process outright to verify, don't rely on SIGUSR1/2 doing a
style reload unless that's explicitly wired up in the bar's own config.

Re-verified live after the real restart, at full bar height this time
(41px, not the 30px guess used previously) specifically to separate the
number glyph's own pixels from the actual underline: rows 15-23 showed
solid Red at both workspace numbers' x-positions equally (confirming
the brightness fix), and rows 32-33 showed a long, contiguous solid-Red
run spanning the *focused* workspace's full button width only -- nothing
at the unfocused-but-occupied workspace's position in those rows. Number
brightness: fixed and equal. Underline: still exclusively on the
focused one. Exactly the intended design.

## Workspace indicator: occupancy as its own signal, separate from focus

Asked for the workspace numbers in waybar to show which workspaces hold
at least one window, everywhere -- not just at the currently-focused
one. Concretely: the focused workspace keeps both its number colored
*and* underlined (unchanged from before); any other workspace holding a
window gets its number colored too, just without the underline, so
"you are here" (underline) and "something's running there" (number
color) read as two independent signals rather than one conflated one.

waybar's `sway/workspaces` module already tracks exactly this itself --
confirmed straight from its own source
(`src/modules/sway/workspaces.cpp`): every workspace button gets an
`.empty` CSS class toggled live, added whenever that workspace's
`nodes` + `floating_nodes` are both empty. No IPC polling or extra
script of our own needed -- waybar was already computing "does this
workspace hold a window" every single update, just never exposing it as
a distinct visual state in this stylesheet.

New rule: `#workspaces button:not(.empty):not(.focused)` -- number-color
only, explicitly `:not(.focused)` so the existing `.focused` rule always
wins outright on the one workspace that's both occupied and current
(solid color + underline), rather than the two rules fighting over the
same element. Colored the same Red as `.focused`, just translucent
(`rgba(243, 139, 168, 0.7)`) rather than solid -- deliberately not a
fourth unrelated hue: one color family read at two strengths says
"these are the same *kind* of signal, at different degrees" far more
clearly than reaching for e.g. Peach or Teal would, and keeps the
underline as the one and only "current" signal instead of also having
to double as an occupancy signal. Placed *before* the existing `:hover`
rule in the stylesheet on purpose -- same selector specificity as
`:hover`, so on a tie the later rule wins; hovering an occupied,
unfocused workspace needs to still show hover's Lavender, not lose to
this new rule.

Verified live, not just reasoned about: two real workspaces existed at
test time, one focused with a window (workspace "2", kitty) and one
unfocused with a window (workspace "1", zen) -- confirmed via
`swaymsg -t get_tree` first, then screenshotted the actual bar and
searched for both the solid-Red and translucent-Red-over-background
colors specifically: 42 pixels matched solid Red (the focused number),
25 matched the translucent blend (the unfocused-but-occupied number) --
two distinct numbers, two distinct intensities, exactly as designed.

## Notification toast icons, round two: currentColor makes symbolic icons invisible on dark backgrounds

Follow-up to "Notification toast icons" below: reported directly after
that fix, specifically about the notification-history.py copy action --
"it fires the notification that the notification is copied but it does
not show the clipboard icon only text". The `icon-path` fix below was
real and necessary, but its own writeup's claim that it "covers all of
them" was wrong -- it fixed *resolution* (mako can now find every icon
name), not *visibility* (whether the resolved icon is actually
perceptible once drawn). Those turned out to be two separate bugs.

**Root cause, found by reading the actual SVG, not assumed**: every
single `-symbolic`-suffixed icon in Papirus (and several of its plain
`actions`-category icons too, e.g. `edit-copy`, `audio-volume-high`,
`media-record`, `process-stop` -- the *symbolic style*, just without the
`-symbolic` suffix on the name) uses `fill:currentColor` with a `style`
block declaring `.ColorScheme-Text { color:#444444; }` as the default --
a dark charcoal gray, designed for GTK's own symbolic-icon recoloring
convention on *light* UI chrome (toolbars, panels). mako just renders
the raw SVG with no theme-aware recoloring -- there's no mechanism in
mako to override `currentColor`. On this desktop's near-black
(`#11111B`) notification background, a `#444444` icon is barely
distinguishable from the background it's sitting on: verified directly
by diffing two real screenshots pixel-by-pixel in the icon's own region
(one with `edit-copy-symbolic`, one with a deliberately nonexistent icon
name as a control) -- 7114 pixels genuinely differed between them, so
something was drawing, just not anything a person would actually notice
at a glance. This is almost certainly the real shape of "shows the text
but not the icon": not a missing icon, an invisible one.

**Fix**: swapped every affected icon reference, across every script in
this repo, from a symbolic/action-style name to Papirus's `status` or
`apps` category equivalent instead -- those use real, hardcoded
`style="fill:#hexcolor"` values (confirmed per-icon with
`grep -c currentColor` returning 0 before using any of them), the same
"regular", full-contrast style Docker's own icon already used
successfully in the first pass. Two icons (`process-stop`, `media-record`)
have no real-fill equivalent anywhere in Papirus at all -- only ever
defined in the `actions` category, always `currentColor` -- swapped for
the closest real-fill concept instead: `dialog-warning` (real amber) for
"cancelled" actions, `audio-input-microphone` (real fill, `devices`
category) for "recording".

Also switched every one of these to an **absolute file path** rather
than a bare theme name, even where a real-fill icon does exist under a
plain name -- several names (e.g. `weather-clear`, `audio-volume-high`)
resolve to *multiple* files across different Papirus categories, one
`currentColor` and one real-fill, and mako's own search algorithm picks
by size-match, not by category -- nothing in the name itself lets you
choose the good one. An absolute path removes that ambiguity entirely,
matching how this repo's own wallpaper/screenshot notifications already
pass a real file path rather than a theme name.

**Verified live**, not just reasoned about, for the two most visually
distinct cases: fired the exact notify-send call
`notification-history.py`'s copy action uses, screenshotted it, and
found 617/413 pixels at the clipboard icon's own known fill colors
(`#e4e4e4`/`#d3d3d3` from the SVG source) in the icon region -- a
deliberately nonexistent-icon control notification, diffed pixel-by-
pixel against the same region, differed by 4194 pixels, confirming this
wasn't incidental. Separately fired a critical-urgency notification with
the new `dialog-error` icon and found 1082 pixels of its own real red
fill (`#f44336`) in the same region. Every other icon across every
other script in this repo shares the exact same `status`/`apps`-category,
real-fill, absolute-path pattern -- not independently screenshot-tested
one by one (would be the same test repeated a dozen times for the same
already-proven mechanism), but each one's source SVG was individually
confirmed `currentColor`-free with `grep` before being chosen, the same
discipline as every icon-existence check already established this
session.

**One file left untouched on purpose**: `notification-history.py`'s
`FALLBACK_ICON` (`dialog-information-symbolic`, used for the small icon
shown next to each row inside the history *list* itself, via
`resolve_icon()`+GTK's own `Gtk.IconTheme.lookup_icon()`, not mako) is a
genuinely different rendering surface -- wofi's own background is the
light "glass" one from an earlier pass in this session (`wofi text
color: black, not white -- hard to notice on the glass background`), not
mako's dark one, so a dark `#444444` default there is plausibly *correct*
contrast rather than the same bug. Left as-is rather than fixing a
problem that may not actually exist there without directly verifying it
first -- out of scope for what was actually reported this round.

## Notification toast icons: a real mako icon-path bug, not a per-icon problem

Asked for every notification toast to show the associated tool's own
icon next to its title (a copy event showing a clipboard icon, Docker
showing its icon, etc.) -- reported again after an earlier pass this
session already fixed `docker-picker.py`'s icon *name*
(`utilities-terminal` -> `docker-desktop`). Every notify-send call
across this repo's scripts already passes a real, correctly-named icon
(`docker-desktop`, `edit-copy-symbolic`, `dialog-error-symbolic`, actual
image paths for the wallpaper/screenshot notifications, etc.), so the
question was why none of them were ever actually appearing.

**Root cause, found in mako's own filesystem behavior, not assumed**:
mako does not do GTK-style icon-theme resolution or theme inheritance --
its own docs say plainly it only ever searches `/usr/share/icons/
hicolor` and `/usr/share/pixmaps` by default, plus whatever `icon-path`
is explicitly configured (empty here, until this fix). This desktop's
actual active icon theme is `Papirus-Dark`
(`gsettings get org.gnome.desktop.interface icon-theme`) -- confirmed
directly with `find` that not one of the icon names this repo's scripts
use (`docker-desktop`, `edit-copy-symbolic`, `dialog-error-symbolic`,
`weather-clear-night-symbolic`, `bluetooth-active-symbolic`, ...) exists
anywhere under `hicolor`. Every single notification's icon was silently
failing to resolve and falling back to no icon at all, regardless of how
correct the icon name passed to notify-send was -- this is almost
certainly the real shape of "notifications don't show icons", not a
per-script naming issue (the docker-picker.py fix from earlier this
session picked a *better* name, but it still wouldn't have rendered
without this).

Also confirmed directly: `Papirus-Dark` itself is nearly empty (3972
files, mostly dark-tinted folder/places variants) and its own
`index.theme` declares `Inherits=breeze-dark,hicolor` -- but mako
doesn't follow icon-theme inheritance either, and breeze-dark isn't even
installed on this machine. The full `Papirus` theme (65991 files) is
what actually has every icon this repo's scripts reference -- confirmed
directly, every single icon name used anywhere in this repo resolves
under it. Fix: `icon-path=/usr/share/icons/Papirus-Dark:/usr/share/icons/
Papirus:/usr/share/icons/Adwaita` in `mako/config` -- Papirus-Dark first
for anything it does override, full Papirus for the actual icon set,
Adwaita last as a broad fallback for anything future scripts reach for
that Papirus doesn't ship.

**Verified live**, not just reasoned about: fired a real notification
with `-i docker-desktop` after the fix and reloaded mako
(`makoctl reload`, config-only, no restart needed -- doesn't hit the
mode-reset bug documented below since the daemon process itself never
restarts); screenshotted the notification region and searched for
Docker's own brand blue (`(28,144,237)`) as an exact pixel match --
716 matching pixels, clearly a real rendered icon, not noise. Negative
control: same test with a deliberately nonexistent icon name --
0 matching pixels, confirming the color match in the first test wasn't
coincidental and the test methodology itself is sound. Every other icon
name in the repo already confirmed present under the same Papirus tree
via `find` before this, so this one fix in `mako/config` covers all of
them -- no other file needed to change.

**One shape worth stating plainly**: mako places a single icon to the
left of the whole notification box (title + body together,
`icon-location=left`, mako's own default, unchanged here) -- it does not
support an icon embedded inline inside just the title text itself. "The
title should have the clipboard svg in it" reads most naturally as
wanting the tool's icon visibly associated with that notification at
all, which this fix delivers; it's not literally inside the title
string, because mako has no mechanism for that.

## Three notification modes: normal/silent/dnd, sound, and a persistence gap

Asked for three notification modes (normal: popup + sound; silent:
popup, no sound; dnd: neither, but still recorded to history), a
pleasant sound, mode-dependent waybar bell icon, and both keybindings and
scroll to switch -- "soft and flawless".

**mako already has the exact right native mechanism for this** -- not
something to build from scratch. `[mode=name]` config sections apply
conditionally based on the current mode (`makoctl mode -s name`), and
`invisible=1` inside one suppresses the popup without touching whether
the notification gets recorded. Confirmed both independently with the
notification's own distinctive Mauve border color as a screenshot signal
(a much more reliable check than generic "non-background pixel count",
which turned out to just be picking up wallpaper content at one point,
caught by comparing against a clean baseline with zero mauve pixels
before trusting any of the mode-specific measurements).

**Sound**: `on-notify=exec paplay file` -- documented directly in
mako's own man page as the intended mechanism, not invented. Picked
`/usr/share/sounds/freedesktop/stereo/message.oga` (the standard
freedesktop sound theme's "new message" chime) by checking every
plausible candidate's actual duration with `ffprobe` first rather than
guessing from the filename -- 0.3s, the shortest of the real candidates,
appropriate for something that can fire on every single notification;
the next-shortest option runs a full second. It's also the literal file
mako's own docs use as their own example.

**Three real bugs found and fixed while building this, each caught by
testing the actual behavior rather than trusting the config or a
plausible-sounding assumption:**

1. **A global option placed after a section header gets silently scoped
   to that section.** The sound line, first added after `[urgency=high]`,
   only ever fired for high-urgency notifications -- normal-urgency ones
   (the vast majority) got no sound at all, with zero parse error to
   flag it. mako's config format scopes every option to whichever
   section most recently opened above it; there's no way to tell this
   from the option line itself. Fixed by moving it before any section
   header, into the true global block.
2. **`invisible=1` does not also cancel `on-notify`.** An early version
   of `[mode=dnd]` had only `invisible=1`, on the assumption that "no
   popup" would obviously mean "no sound either" for a mode literally
   named after suppressing everything. It doesn't -- confirmed directly
   with an unambiguous marker-file side effect on `on-notify` (touch a
   uniquely-timestamped file, decoupled from actually needing to *hear*
   anything), which fired even in `dnd` mode. Needs the same explicit
   `on-notify=none` as `[mode=silent]` -- `none` specifically, not an
   empty value (`on-notify=` alone fails to parse at all, confirmed
   directly: `"Failed to parse option 'on-notify='"`).
3. **Mode state doesn't survive a mako restart.** `makoctl mode` resets
   to mako's own built-in "default" the moment mako restarts (crash,
   manual restart, reboot) -- confirmed directly by killing and
   restarting mako mid-test and checking `makoctl mode` immediately
   after. Without a fix, choosing `dnd` once would silently drop back to
   full popups-and-sound on every login with no indication anything
   changed. Fixed the same way `caffeine-toggle.sh`'s own state survives
   a reboot elsewhere in this repo: a persisted state file
   (`~/.local/state/notification-mode/current`) plus a startup script
   (`notification-mode-restore.sh`, run right after `exec mako` in
   `sway/config`, with the same bounded-retry pattern
   `swayidle-startup.sh`/`fetch_wallpaper.sh` already use for the
   analogous "the thing I need to talk to isn't up yet" race) that
   reapplies it every time mako starts.

**Mode naming**: `normal`/`silent`/`dnd` are plain custom mode names with
no `[mode=normal]` section of their own for the first one -- confirmed
live that an undefined mode name is a clean no-op (every global setting
applies unchanged, verified with the same Mauve-border-plus-marker-file
check as the other two modes), rather than relying on mako's own
built-in "default" mode, which mako's own docs flag as deprecated and
due for removal in a future version.

**Switching**: `scripts/.local/bin/notification-mode.sh
normal|silent|dnd|next|prev`. Direct-jump keybindings
(`$mod+Ctrl+n`/`-s`/`-d`) for "I know exactly which mode I want", plus
`$mod+n` and the waybar bell's scroll wheel (`on-scroll-up`/`-down` in
`waybar/config`) both calling `next`/`prev` for quick cycling -- verified
the cycling math directly (`normal -> silent -> dnd -> normal` forward,
correctly symmetric in reverse), not just eyeballed. The waybar `custom/
notifications` module also got a `"signal": 8` entry, triggered via
`pkill -RTMIN+8 waybar` at the end of every mode switch -- the actual
mechanism behind "soft and flawless": the bell's icon and color update
the instant you switch, not on the module's own 5s poll interval.
Confirmed with a real keybinding switch to `dnd` and finding the bell's
color had already changed to Red in a screenshot taken immediately after,
not waited out to the next poll.

**A deliberate design choice worth stating plainly**: the mode-change
confirmation notification itself follows whatever mode it just switched
into -- switching into `dnd` means that confirmation doesn't pop up
either, which is consistent (dnd meaning "no popups, ever" shouldn't have
a built-in exception for its own confirmation) rather than a gap. The
waybar icon's instant update via the signal above is the actually-
guaranteed-visible confirmation regardless of mode; the notification is
extra, always still landing in history either way.

**Waybar bell icon** (`notification-history-status.sh`): reads the
persisted state file, not `makoctl mode` directly, keeping this the same
single source of truth every other part of this feature already treats
as authoritative rather than a second one that could theoretically read
racy live daemon state mid-switch. Went through three rounds on the icon
itself, each a direct response to feedback: three different glyphs
(`fa-bell`/`fa-bell-slash`/`md-minus-circle`) first -> asked for
white-only, reconsidered mid-request, dropped to one shared `fa-bell`
with color as the only signal -> asked again for distinct glyphs per
mode, landed on the current design: **both** shape and color change per
mode, reinforcing rather than duplicating each other. All three stay in
the bell family rather than reaching for an unrelated glyph like the
original `md-minus-circle` for dnd, so it still reads as "the
notification bell, in a different state" at a glance rather than a
different icon entirely: `fa-bell` (normal), `fa-bell-slash` (silent --
the standard "muted" bell), `md-bell-sleep` (dnd -- a bell with "zzz",
distinct silhouette from bell-slash, and conceptually fits "do not
disturb" better than a generic prohibition glyph). All three codepoints
confirmed present in the installed JetBrainsMono Nerd Font via
`fc-list ":charset=hex"` before use, same discipline as every other
icon chosen this session, and the PUA-glyph-transport-corruption bug
that's recurred repeatedly all session hit again writing these three --
caught and fixed the same way as always: patch via Python `chr(0xXXXXX)`
directly into the file, then read back and check `hex(ord(ch))` per
glyph rather than trust the literal in the edit call.

Colors: Lavender for normal, dim gray for silent (matching every other
"quieted, not fully off" state elsewhere in this bar), Red for dnd (the
one state here that's an active, deliberate choice to suppress
everything, worth a real attention color). Picked specifically checked
against `#clock`'s own colors (Blue for the time, Maroon for the date,
right next to this module) so the mode color doesn't get lost against
or mistaken for the clock -- confirmed with an exact-pixel-color
screenshot count per mode (a hand-rolled pure-Python PPM parser, since
this machine has neither Pillow nor ImageMagick installed and no sudo to
add them; `grim -t ppm` was the workaround): each mode's own color is
the dominant exact match in the bar while active, and none of the three
notification colors share a single exact pixel match with either clock
color in any mode.

**Not independently mouse-tested**: same disclosed limitation as
`notification-history.py`'s own waybar click a few passes back --
`ydotool`'s absolute mouse positioning has an unmet calibration
requirement in this environment, so scroll-over-the-bell-icon couldn't
be cleanly verified with a real wheel event. What *is* fully verified:
the underlying `next`/`prev` cycling logic directly (both directions,
symmetric wraparound), and both keybinding paths via real simulated
keypresses. The waybar `on-scroll-*` wiring calls the identical script
with the identical arguments as the verified keyboard path -- the same
inference-from-proven-pattern basis as the click path, not an
independent scroll test.

## Notification history viewer, and a real docker-picker.py icon bug

Asked for two things: a real docker-branded icon on Docker notifications
(reported directly -- "only has the docker name in it not the icon of
it"), and a notification history viewer (waybar bell, left of the clock,
newest-first, showing full details).

**The icon bug**: `docker-picker.py`'s `notify()` used `utilities-
terminal` for its non-critical case -- a generic terminal glyph with no
connection to Docker at all. Papirus (installed since the icon-pack
pass) ships a real `docker-desktop` icon -- confirmed it actually
resolves via the same GTK icon theme lookup every other themed icon on
this system goes through (`Gtk.IconTheme.get_default().lookup_icon(...)`)
before using it, not assumed from the filename (a bare `"docker"` name
does *not* resolve to anything in Papirus, `"docker-desktop"` does).
Fixed; verified live by firing a real notification and confirming
substantial non-background pixel content actually renders in the icon's
expected screen position, the same discipline already used for every
other icon audit in this repo.

**`notification-history.py`**: mako already has a real history buffer
(`makoctl history -j`) -- just needed `history=1`/`max-history=200`
turned on in `mako/config` (off by default, nothing to show without it).
Reads it, resolves each entry's `app_icon` through the same GTK icon
theme lookup as above (works for both theme-name icons and the couple of
this desktop's own notify-send calls that pass an actual image path,
e.g. the wallpaper/screenshot success notifications), and shows it as a
wofi list.

Two real bugs found and fixed while building this, both by testing the
actual behavior rather than trusting assumptions:

1. **mako's own history ordering isn't reliable.** One `makoctl history
   -j` call came back newest-first, a later one (same kind of data, same
   machine) came back oldest-first. `id` increments monotonically
   regardless, so the script now explicitly sorts on it descending
   rather than trusting whatever order the command hands back --
   "newest first" was an explicit requirement, not something to leave to
   chance.
2. **wofi's dmenu input splits on newline into separate entries** --
   found by testing the actual selection round-trip, not assumed from
   "labels wrap" alone (which is real, but is about one long *single*
   line wrapping at the window edge, a completely different thing from
   an embedded `\n` staying inside one logical entry). An embedded `\n`
   between a notification's summary and body silently produced two
   *separate* dmenu items instead of one two-line one -- confirmed
   directly by piping a two-line `img:...:text:` value in and checking
   exactly what came back on selection: only the first line, as its own
   entry. Fixed by keeping one line per notification (summary and body
   joined with a visible separator, same pattern already used for
   `docker-picker.py`/`wifi-picker.py`'s own single-line info rows) --
   long ones still wrap naturally within that one entry, which was
   confirmed working separately.

**"Shows full details on focus", the literal ask, isn't architecturally
available in wofi's dmenu mode** -- confirmed rather than assumed:
there's no focus-change hook or live preview pane in how wofi's own
dmenu list works, just a single "output the selected line on Enter"
model. The honest equivalent built instead: every entry already shows
its full summary and body up front (relying on the confirmed-real label
wrapping for long ones), so there's nothing further to reveal on focus
in the first place. Selecting an entry copies its text to the clipboard,
matching the same pattern already used elsewhere in this desktop
(`wofi-calc.sh`, `keybind-search.py`) instead of being a no-op.

Added `$mod+Shift+n` (`sway/config`), matching the same keyboard-path
convention as every other waybar-click picker in this repo, and
confirmed live via a real `ydotool`-simulated keypress. The waybar
`on-click` path itself uses the identical JSON structure as every other
already-verified picker module in this config (`docker-picker.py`,
`theme-toggle.sh`) -- **not independently re-verified via a real mouse
click this pass**, disclosed rather than silently assumed: `ydotool`'s
absolute mouse positioning has a documented calibration requirement
("disable mouse speed acceleration for correct absolute movement") not
met in this environment, and clicking at a pixel-sampled icon position
reliably landed on a different module instead (confirmed by checking
waybar's own log for which script actually fired). The keyboard path is
fully verified; the on-click path rests on it being the same proven JSON
pattern as its siblings, not an independent click test.

## Theme toggle robustness: verified the whole chain, found a real gap

Reported the toggle fires notifications but Zen Browser (set to follow
the system theme) never actually switched to light. Verified every layer
of the mechanism directly rather than guessing which one was broken:

1. `dconf write` itself -- confirmed the value actually changes
   (`dconf read` immediately after).
2. The XDG Desktop Portal's `Settings.Read` -- queried
   `org.freedesktop.appearance`/`color-scheme` directly via `gdbus call`
   and confirmed it echoes back the new value the instant dconf changes,
   not a stale/cached one.
3. Whether the portal actually **emits a live change signal**, not just
   answers correctly on-demand -- this is the one that matters for an
   already-running app to update without a restart. Ran `gdbus monitor
   --session --dest org.freedesktop.portal.Desktop` while triggering the
   toggle: `SettingChanged` fired correctly, with the right new value, on
   *both* the legacy `org.gnome.desktop.interface` namespace and the
   newer `org.freedesktop.appearance` one. This layer is genuinely,
   verifiably working.

**The real bug**: `catppuccin-gtk-theme-latte`, `papirus-icon-theme`, and
`papirus-folders-catppuccin-git` -- the packages added to `packages/
aur.txt`/`packages/pacman.txt` when this toggle was first built -- were
never actually installed (confirmed: `pacman -Q` fails for all three; the
handed-off install command hadn't been run). `theme-toggle.sh` was
writing `gtk-theme`/`icon-theme` dconf keys pointing at those names
unconditionally, light or dark, regardless of whether anything was
actually installed under `/usr/share/themes`/`/usr/share/icons` for
them. A GTK theme/icon-theme name that doesn't resolve to anything
installed doesn't fail loudly -- native GTK apps just silently keep
rendering whatever they last successfully loaded, which looks
indistinguishable from "the toggle did nothing."

**Fixed**: `theme-toggle.sh` now checks `/usr/share/themes/name` and
`/usr/share/icons/name` directly before writing either dconf key, and
skips writing it (leaving the previous, working value in place) if the
target isn't actually there -- with a clear notification naming what's
missing and pointing at the install command, rather than silently
pretending everything applied. `color-scheme` is always written
regardless of any of this, since it's a pure preference value with no
file dependency, and is the one signal apps like Firefox/Zen actually
need for their own internal dark/light CSS switching -- they don't
render using arbitrary system GTK theme files the way a native GTK app
does. Verified the fix directly: ran the toggle with the packages still
missing, confirmed `color-scheme` and the already-installed dark GTK
theme switched correctly while the not-yet-installed light GTK
theme/icon theme were left alone (not overwritten with a broken
reference), and confirmed the notification text names exactly what's
missing.

**What's confirmed working but genuinely outside this repo's reach**:
whether a specific app actually *subscribes* to the portal's
`SettingChanged` signal is up to that app, not anything on the desktop
side. Firefox-based browsers specifically have a
`widget.use-xdg-desktop-portal.settings` preference (`about:config`)
gating whether they use the portal for this at all -- if a browser stays
on its last-detected appearance after a verified-correct toggle, that
preference is the first thing worth checking, since it's inside the
browser's own settings, not reachable from a desktop config.

### Follow-up: confirmed live that Zen Browser genuinely wasn't reacting

After the packages were actually installed and the fix above shipped,
still reported Zen staying dark. Zen was genuinely running at the time
(confirmed real PIDs, not assumed), so this got a direct answer instead
of more theorizing: screenshotted the desktop, pixel-sampled Zen's own
toolbar/chrome area, and found consistently near-black colors while
`dconf read color-scheme` reported `'prefer-light'` at that exact moment
-- concrete, first-hand confirmation Zen's chrome wasn't reacting, not
just trusting the report.

Traced it to that same `widget.use-xdg-desktop-portal.settings`
preference. Its default is `2` (auto-detect: use the portal only if
GTK build + Wayland + portal available), and every one of those
conditions is genuinely true here -- yet it evidently wasn't resolving to
"use it" in this specific Zen build/environment. Applied the fix
directly: `user_pref("widget.use-xdg-desktop-portal.settings", 1);` (force
always-on) in `user.js` in Zen's actual active profile, found via its
`lock` file pointing at the real running PID rather than guessing which
of the two profile directories under `~/.config/zen/` was in use.

**Deliberately not added to this repo's stowed config**: Firefox/Zen
profile directory names are randomly generated per-install (this
machine's is `l23hrxpc.Default (release)`), not stable or portable the
way every other config in this repo is -- there's no fixed path a stow
package could symlink into. This fix lives only in that profile's
`user.js` on this specific machine; a fresh install (or a new profile)
would need the same fix applied again manually, a real, disclosed
limitation rather than something silently assumed to carry over.
`user.js` only gets read at Zen's own startup, not live -- needs a
restart to actually take effect, not applied automatically here since
restarting someone's browser out from under their open tabs isn't this
repo's call to make.

## A real incident: stow symlinks silently broken across the whole desktop

Reported the docker waybar module's click had stopped opening the wofi
popup, and asked for a keybinding matching the other pickers. Chasing the
click issue found something much bigger: `~/.config/waybar/config` was a
**real file**, not the symlink stow is supposed to maintain -- and
checking further, so were `~/.config/sway/config`, both wofi files, mako,
nwg-bar, kitty's `kitty.conf`, tmux's `tmux.conf`, every tracked file
under `~/.config/nvim/` and `~/.config/zed/`, and
`~/.config/systemd/user/tmux.service` was missing outright (the exact
symlink fixed earlier in an unrelated pass -- gone again).

**What almost certainly caused it**: this is a well-known dotfiles-via-
symlink gotcha, not something specific to this repo's own scripts.
Editors and tools that save "atomically" (write a temp file, then
`rename()` it over the target, to avoid partial writes) replace whatever
is at that path -- which, for a symlink, means the symlink itself gets
replaced by a real file containing the new content, permanently
disconnecting it from the repo. This happens the moment *anything* saves
a symlinked config file directly rather than through the repo path, and
explains why files this session never touched (all of `nvim`, `zed`) were
affected too -- not unique to anything done in this conversation.

**Checked before touching anything**: diffed every affected file against
its repo counterpart. All content-identical (except the two `nvim` files
already tracked as long-standing local drift, also identical to the
repo's own uncommitted copy) -- confirmed safe to just re-link, not a
case of real unsaved state that would need reconciling first.

**A second, more serious mistake made while fixing this, disclosed in
full rather than glossed over**: fixed a few files individually, then
tried to fix the rest faster with one bulk call --
`stow -R -t ~ sway waybar wofi mako nwg-bar kitty tmux nvim zed
networkmanager-dmenu systemd` covering every affected package at once.
This **deleted the repository's own source files** for all of them --
confirmed via `git status --short` afterward showing 32 files as
deleted in the working tree. Root cause: GNU Stow's directory-folding
logic, when several of its targets are simultaneously real files instead
of the symlinks it expects, can behave unpredictably on a combined
restow across many packages at once -- exactly the situation this bulk
call created by design (mixing several inconsistent live-target states
into a single stow invocation).

**No data was actually lost**: git history is the real source of truth
here, and none of this touched it -- `git log` was intact throughout,
and `git restore .` brought every file back exactly as committed in one
command. Verified thoroughly before considering this closed, not just
trusting a clean `git status`: re-checked file line counts and grepped
for the most recent real content (`custom/theme`/`docker-picker`
references in `waybar/config`) to confirm actual restoration, not just
an empty diff.

**Fixed properly the second time**, one package at a time instead of a
combined bulk call, verifying after each: `rm` the broken real files, a
single `stow -R -t ~ one-package`, confirm the result is a real
symlink before moving to the next package. Final state verified three
ways -- every `~/.config/pkg` directory is a genuine whole-directory
symlink (`ls -la` showing `lrwxrwxrwx`), `git status --short` clean, and
`stow -n -v -t ~` (dry-run) across every package in the repo reporting
zero pending actions.

**The lesson, worth keeping in mind going forward**: never edit a
symlinked dotfile at its live `~/.config/...` path directly -- always
through the repo path (`~/dotfiles/...`), which this session has done
consistently, but doesn't protect against *other* tools (editors, plugin
managers, anything with "safe save" behavior) doing it. A periodic
"are all my stow symlinks still symlinks" check (exactly the loop used
to discover this) would catch this early next time, before it silently
accumulates across an entire desktop's worth of configs.

With everything actually reconnected, the docker click started working
immediately -- confirmed live via `ydotool`-simulated `\$mod+d`-style
keypresses on the new keybinding below, not just a manual script
invocation. Also added `\$mod+Shift+d` (`sway/config`), matching the
exact convention already used for `\$mod+Shift+w`/`\$mod+Shift+b` --
`docker-picker.py` had been waybar-click-only, the same gap Wi-Fi and
Bluetooth had before their own keybindings were added. Automatically
picked up by `keybind-search.py` with no further work, confirmed live.

## Gutters between wofi entries

Asked to increase the gap between rows/columns. wofi has no dedicated
row-spacing/column-spacing option -- checked `--help` and the man page,
neither exposes one -- so this is the standard GTK-CSS technique instead:
`margin` on `#entry` itself (the FlowBox child), not something set on the
container. `5px` on every side, which shows up as a real gutter between
tiles in the app launcher's grid and as breathing room between rows in
every other wofi-backed tool's single-column list, since they all share
this one `style.css`.

Verified with the same real-keypress method the app-launcher-grid bug
above required: simulated `$mod+d` and `$mod+Shift+w` with `ydotool`,
screenshotted, and confirmed two things directly rather than assumed --
the grid still fits 4 real columns with the new margin eating into
available space (found the same 4 evenly-spaced structural boundaries as
before), and a real, consistent ~11px vertical gap now exists between list
rows (close to the expected 5px margin + 1px border on each adjacent
entry, `2*(5+1)=12`, matching within normal antialiasing rounding).

## The app launcher grid's real bug: a bare comma inside `exec`

Reported a second time that `$mod+d` still showed a single column, after a
fix that looked, by every check run so far, like it should have worked. It
didn't, and the reason was worth chasing down properly rather than
re-guessing at CSS again: **every verification up to this point had been
testing the wrong thing.**

Every earlier test ran the wofi command manually, in a plain background
shell (`wofi --show drun,run --columns 4 --width 60% &`). That never goes
through sway's own `exec` command parsing at all -- it's just a shell
directly running a program, and it worked every time. The actual
`$mod+d` keybinding runs through sway's `exec`, a completely different
code path, and had never once been tested directly until this pass --
confirmed by literally simulating the real keypress with `ydotool` (kernel-
level input injection, indistinguishable from a real key event, already
used elsewhere in this repo for capslock/numlock) and comparing the
*actual running process's command line* against what was configured.

The real process launched by a genuine `$mod+d` press was `wofi --show
drun` -- no `--columns 4` at all. Root cause: sway's config syntax uses a
bare comma to chain multiple commands on one `bindsym` line (`bindsym x
cmd1, cmd2`), and `exec`'s own argument isn't exempt from that parsing --
a literal comma anywhere in the string handed to `exec`, even one meant
for the program being launched rather than sway itself, gets treated as a
command separator. `wofi --show drun,run --columns 4` was silently
truncated to `wofi --show drun` the instant `exec` ran it, dropping
`--columns 4` along with the rest. This is exactly why "still shows a
single column" persisted through what looked like a correct fix: the flag
was never reaching wofi in the first place, so no amount of CSS or width
changes could have touched it.

Fixed by dropping `",run"` from `$menu` -- `--show drun` alone has no
comma to trip over. "run" mode (launch an arbitrary `$PATH` executable by
typed name, separate from the `.desktop`-entry app database `drun` reads)
wasn't actually part of what was asked for ("application search")
regardless, so this isn't a workaround masking a lost feature, just
dropping something that was never the point. Reverified with the same
real-keypress-plus-process-inspection method, twice, before trusting it:
the running process now genuinely is `wofi --show drun --columns 4`.

**The methodological lesson, worth keeping in mind for anything bound to
a key in this desktop going forward**: a command that behaves correctly
when run directly is not proof that the *same* command behaves correctly
when run through `exec` from a `bindsym`. They are different code paths,
and sway's own comma-as-separator parsing is exactly the kind of thing
that only shows up in the second one.

Also acted on directly in this pass: moved `width=60%` into the shared
`wofi/config` (was previously repeated as `--width 60%` on `$menu` and on
`keybind-search.py`'s own wofi invocation separately) so every wofi popup
in this desktop uses it from one place, per request -- removed both of the
now-redundant per-invocation flags rather than leaving three copies of the
same value to drift out of sync with each other.

## Wi-Fi/Bluetooth pickers, keybind search sizing, and an "uneven" app grid

Three follow-up requests on the wofi work above:

- **Wi-Fi and Bluetooth pickers had no keyboard path at all** -- both
  `wifi-picker.py` and `bluetooth-picker.py` existed only as waybar
  `on-click` handlers (mouse-only). Added `$mod+Shift+w` / `$mod+Shift+b`
  in `sway/config`, same scripts, no changes to either picker itself.
  Automatically picked up by `keybind-search.py` with no extra work, which
  is the entire point of that tool reading live config instead of a
  maintained list -- but caught the same comment-structure gotcha its own
  keybinding hit earlier: a multi-line comment's *last* line is what
  becomes the search description, so leading with the "why" ("previously
  only reachable by clicking...") and trailing with a clean one-line
  description right above the `bindsym` (matching the fix already
  documented for `keybind-search.py`'s own entry) rather than the reverse.
- **Keybind search widened to 60% of screen width, height trimmed
  moderately**: `--width 60%` (wofi does support percentage width/height
  values -- confirmed via `swaymsg -t get_outputs`'s `layer_shell_surfaces`
  extent reporting back exactly `1152` on a 1920px output, not assumed
  from a docs description) and `--lines 15` -> `12` (measured extent
  647px -> 536px tall, roughly a 17% reduction -- "not much but some").
- **`$mod+d`'s app launcher in a grid, not a plain list**: `--columns 4`,
  added only to `sway/config`'s `$menu` variable, not the shared
  `wofi/config` every *other* wofi-backed tool in this desktop also reads
  -- a grid would break the readability of a single-column list like the
  Wi-Fi picker or calculator. wofi's grid mode is a GtkFlowBox under the
  hood, which sizes each entry to its own icon+label content rather than
  a fixed cell width, which is what makes it read as an uneven, organic
  grid instead of uniform cards.

  **First verification pass here was wrong, and worth recording why**:
  checked for "discrete content blocks with gaps" in a screenshot and
  called it done -- but never actually counted how many columns were
  rendering. Reported back that the launcher still showed a single
  column. Re-checked properly this time (clustering content by x-position
  per row, not just presence of gaps) and found the real cause: at the
  shared config's default 600px width, `--columns 4` only ever produced
  2 real columns -- real installed app names ("Beekeeper Studio",
  "Bluetooth Adapters") are wide enough that GTK's `max-children-per-line`
  acts as a ceiling, not a forced count, and 600px only fits 2 at a
  readable size. On a machine with even longer app names this could
  plausibly collapse to 1, matching what was reported. Fixed by widening
  to `--width 60%` (same convention as keybind-search.py's popup) --
  reverified the same way and found 4 genuine columns, evenly spaced.
  The lesson: "gaps exist somewhere" is a much weaker check than "N
  columns actually render," and this is why the width had to change too,
  not just be a separate ask.
- **A real border on every entry**, not just the existing left accent bar
  reserved for the selected state -- asked for specifically so a
  multi-column grid row reads as distinct tiles next to each other, not
  text floating in shared space. First attempt used a very faint 12%
  alpha mauve border; correctly parsed (no CSS errors) but nearly
  invisible on screen once actually screenshotted and checked pixel-by-
  pixel -- not "properly aesthetic" as asked, just technically present.
  Raised to 28% at rest (35%/45% on hover/selected), confirmed this time
  by finding a real, consistent brightness jump at each entry's border
  row versus its neighbors in a screenshot. Still subtle enough at rest
  to work as an ordinary row divider in every other wofi-backed tool's
  single-column list, since this is the one shared `style.css` all of
  them read -- not something that only makes sense in grid mode.

## Wofi's "glass" look: real compositor blur, not just a tinted box

Asked to make wofi look more like glass. The honest first step was
recognizing that a semi-transparent `background-color` alone (what the
previous style had, at 0.95 alpha -- essentially opaque) isn't glass, it's
a dark box with a hint of see-through. Real glass needs something behind
it to actually blur, and GTK3's CSS engine (what wofi's `style.css` is
written in) has no `backdrop-filter` -- that's a much newer CSS Filter
Effects spec feature GTK3 never implemented.

What this desktop already has, unused until now: **SwayFX** (this repo's
actual sway build, `packages/aur.txt` -- a sway fork adding real
compositor-level blur/shadow/corner-radius via `scenefx0.4`, already used
for window shadows and corner rounding, just never wired to any
layer-shell surface). SwayFX's `layer_effects "namespace" { blur enable;
... }` applies real background blur to a specific layer-shell surface by
its namespace. Confirmed wofi's actual namespace live rather than assumed
from the binary name -- `swaymsg -t get_outputs` while wofi was open lists
it under `layer_shell_surfaces` as `"wofi"`.

```
layer_effects "wofi" {
    blur enable
    blur_xray enable
    corner_radius 16
    shadows enable
}
```

`blur_xray enable` blurs the *true* desktop background behind wofi, not
whatever surface happens to sit immediately behind it (a waybar pill it
overlaps, say) -- the difference between authentic frosted glass and
blurring the wrong layer. `corner_radius 16` matches wofi's own CSS
`border-radius` so the blurred/shadowed shape actually lines up with the
window's rounded corners instead of showing a square blur behind round
content.

Verified this is real, not just requested, two ways: `swaymsg -t
get_outputs`'s `layer_shell_surfaces` entry for wofi echoes back
`"blur": true` (confirms the compositor accepted and applied it, not just
that the config parsed), and a direct pixel test -- screenshotted the same
600x400 screen region with wofi closed vs. open (at a near-zero background
alpha specifically to make any underlying blur visible through it),
measured local pixel-to-pixel variance as a sharpness proxy in a
background-only row (away from wofi's own sharp UI chrome, which would
confound the measurement), and found it 4x smoother with wofi open
(edge-variance 6.0 vs. 23.9) -- consistent with real blur, not a rendering
assumption.

With real blur available, `style.css` was rebuilt to actually let it show:

- Background alpha dropped from 0.95 to 0.62 -- enough tint to keep text
  legible, translucent enough for the blur to actually read as present.
- A faint top-edge sheen (`background-image: linear-gradient(...)`,
  layered on top of `background-color` -- GTK CSS supports both on one
  element) fading out by mid-height, mimicking the light-catching highlight
  a real glass/acrylic panel shows at its top edge.
- `#input`'s own border made slightly brighter than the outer window
  border, so the search field reads as sitting a touch closer to you than
  the glass pane behind it, rather than flush with it.
- The GTK default scrollbar (a flat light-gray widget) was left unstyled
  before -- exactly the kind of unstyled-default seam that breaks a glass
  illusion sitting on top of a dark, blurred, translucent panel. Recolored
  to the same Mauve family as everything else, transparent at rest so it
  doesn't compete with the blur when not needed.
- `#entry:hover` added -- there was no mouse-hover feedback at all before,
  only `:selected` (keyboard navigation). A softer wash than `:selected`'s
  keeps the two states visually distinct from each other, not just from
  idle.
- `#entry:selected` gained a 2px left accent bar in the same Mauve, on top
  of the existing background wash -- both idle and hover reserve the same
  2px of transparent `border-left` so the accent appearing on selection
  doesn't shift every row's text over by 2px when it shows up (the same
  layout-jump guard already used for waybar's workspace-button
  hover/focused underline elsewhere in this desktop).
- `wofi/config`'s `image_size` bumped 24 -> 32 for more visual hierarchy
  in `drun` mode's app-icon grid.

All of this lives in the one shared `style.css`/`config` every wofi-backed
tool in this desktop uses -- `drun`/`run`, the wifi picker, bluetooth
picker, calculator, emoji picker, cliphist popup, `networkmanager-dmenu` --
so this one change reaches every one of them, not just the app launcher.
Tested both `--show drun` and `--show dmenu` directly (not just the
launcher) to confirm neither mode broke -- checked stderr for GTK CSS
parse warnings on each (none) before trusting any of this.

## Notification icons: every notify-send call, one real icon each

Every `notify-send` call across this desktop's own scripts (`scripts/.local/
bin/`, `sway/.config/sway/scripts/`) now passes a real icon -- either a
freedesktop icon-theme name (looked up through whatever GTK icon theme is
active; this system only has `adwaita-icon-theme`/`hicolor-icon-theme`
installed, so every name used was confirmed present there first --
`find /usr/share/icons/Adwaita -iname '*volume*'` and the same for every
other icon used, same discipline as verifying a Nerd Font codepoint exists
before using it elsewhere in this repo) or, for the two that have one, the
actual resulting image (`fetch_wallpaper.sh`'s success notification uses the
new wallpaper itself; `screenshot.sh`'s uses the screenshot itself -- both
already existed, untouched here).

Icon choice generally follows the same "urgency/state carries real meaning"
convention already established elsewhere in this desktop (mako's own
`[urgency=high]` border-color override; the battery/lock waybar CSS states):

- **Volume** (`volume_osd.sh`): tiered like waybar's own battery icons --
  `audio-volume-{muted,low,medium,high}-symbolic` depending on the actual
  percentage, not one static speaker glyph regardless of level. The mute
  toggle's notification body also lost a redundant inline Nerd Font glyph
  it had before (`" Muted"`) now that a real icon carries that signal --
  showing the same information twice looked cluttered once the icon existed.
- **Brightness** (`brightness_osd.sh`): `display-brightness-symbolic`.
- **Bluetooth** (`bluetooth-picker.py`): icon follows urgency in the shared
  `notify()` helper -- `dialog-error-symbolic` for the `critical` failure
  cases, `bluetooth-active-symbolic` otherwise.
- **Wallpaper** (`fetch_wallpaper.sh`): `preferences-desktop-wallpaper-
  symbolic` for the in-progress states (fetching / already fetching),
  `dialog-warning-symbolic` for soft failures (kept last-good, couldn't
  apply live), `dialog-error-symbolic` for the no-previous-wallpaper hard
  failure -- severity now visible in the icon, not just readable in the
  text.
- **Everything else** (keylock-toggle's ydotool setup errors,
  wf-recorder/screenshot's "cancelled" notifications, keybind-search.py's
  own error/copied notifications): `dialog-error-symbolic` for genuine
  errors, `process-stop-symbolic` for a cancelled action, `edit-copy-
  symbolic` for the clipboard-copy confirmation.

`mako/.config/mako/config` also got `max-icon-size=48` and `icon-border-
radius=8` -- mako's icons render sharp-cornered and whatever size the source
image happens to be by default, which didn't match the rounded-pill look
used everywhere else in this desktop (waybar's 16px, mako's own 12px outer
`border-radius`). Verified all of this live, not just by reading the mako
docs: fired real test notifications, screenshotted, and confirmed real
non-background pixel content actually renders in the icon's expected
on-screen position (mako anchors `top-right`, so the icon sits in the
bubble's top-left corner) -- catches the same class of "icon name typo'd,
theme lookup silently fails, notification just looks blank" issue this
whole exercise was about avoiding in the first place.

## Keybinding search: `$mod+Shift+slash`, a fuzzy wofi popup over live config

`scripts/.local/bin/keybind-search.py`. Deliberately excludes Neovim -- it
already has its own built-in keymap search -- and covers sway + tmux.

Both sources are re-parsed from the real, live config on every invocation
rather than kept in a separate hand-maintained cheat-sheet file, which would
just be one more thing to remember to update (see the TPM section right
below for what happens when two things that should describe the same state
drift apart):

- **Sway**: reads `~/.config/sway/config`'s own `bindsym` lines directly,
  paired with whatever comment sits above each one -- this file's own
  existing convention already, not something invented for this script.
  `$mod`/`$left`/`$down`/`$up`/`$right` are expanded to their real key names.
  A comment covering a whole group (one comment above 4 arrow-key binds, for
  instance) is reused for each key in that group, with the actual command
  appended in parens to disambiguate which does what -- also fixes a real
  fuzzy-search gap: matching is a subsequence match in query order, so
  typing "workspace 1" wouldn't match an entry whose only "1" appeared
  *before* the word "workspace" (as `Super+1`'s bare comment would have,
  with no command shown).
- **Tmux**: reads `tmux list-keys` (the raw form, explicit `-T table` per
  line -- unambiguous about which key-table a binding is actually on) for
  the key inventory, and sources descriptions from two places: this repo's
  own tmux.conf, which now gives every custom bind an explicit `-N "note"`
  (tmux's own built-in per-binding description mechanism, added specifically
  for this -- see tmux.conf's own comment on it), and tmux's stock built-in
  notes via `tmux list-keys -N` for anything not explicitly customized here.
  A `tmux-resurrect`-installed binding (`C-a C-r`, restore) shows up
  automatically with no special-casing needed, which is exactly the point of
  reading live state instead of a maintained list.

  Two real bugs found and fixed while building this, both from checking
  actual output instead of trusting the format: `list-keys -N`'s compact
  view prefixes *every* line with `C-a`, even root-table binds like `-n
  M-Left` that need no prefix at all -- confirmed via the raw dump's
  explicit `-T root` before trusting it, since taking the compact view at
  face value would have made this tool actively lie about which keys need
  the prefix. And an early version keyed custom notes by bare key name
  alone, which let this repo's prefix-table `r` note ("Reload tmux config")
  incorrectly relabel tmux's *unrelated* stock `copy-mode` binding for the
  same letter (`refresh-from-pane`) -- fixed by keying on `(table, key)`
  instead. Mouse bindings (`Mouse*`/`Wheel*`/`*Click*`) are filtered out
  entirely -- not keybindings, and their commands can run to ~2000
  characters (one wofi/waybar-style menu built from `display-menu`), which
  would both clutter the list and render as one absurd line.

  `wl-copy`, on selecting an entry: written as `Popen` + close stdin,
  deliberately not waited on. Confirmed directly (cliphist picked up a test
  string the instant it was sent) that `wl-copy` sets the clipboard
  immediately but the process itself lingers afterward, since it has to
  stay alive to keep serving that selection to whoever reads it next --
  `subprocess.run`/`.communicate()` both block until the child exits, which
  would hang this script after every single use for no reason.

## The tmux status bar's dependency chain

Worth calling out on its own, since it broke in layers (see changelog): the rounded
separators and the session/docker icons are Nerd Font Private-Use-Area glyphs. They
need *both* the exact right codepoint in `tmux.conf`/`docker_status.sh` *and* a Nerd
Font actually installed and selected in your terminal (`kitty.conf`'s `font_family`).
Missing either one renders as a blank box, and the two failure modes look identical —
if a fresh machine shows boxes, check the font first (`fc-query -f '%{charset}' <font
file>`, and confirm the codepoint tmux is using is actually in there) before assuming
the config is wrong.

## TPM's plugin path: pinned, not left to auto-detection

`install.sh` clones TPM to `~/.tmux/plugins/tpm` and `tmux.conf` sources it from
there (`run '~/.tmux/plugins/tpm/tpm'`), so `~/.tmux/plugins/` looks like the
obvious place TPM manages `tmux-resurrect`/`tmux-continuum` too. It isn't, by
default: TPM's own bootstrap script auto-detects an XDG-style `tmux.conf` (i.e.
`~/.config/tmux/tmux.conf` existing, which it always will here, since that's
exactly where this repo's stow layout puts it) and silently redirects plugin
management to `~/.config/tmux/plugins/` instead -- a *different* directory that
happens to sit inside the stowed repo tree itself, untracked, with each plugin's
own nested `.git` dir. `install_plugins.sh` will happily report "Already
installed" for plugins living there while `~/.tmux/plugins/` only ever has TPM
itself in it -- confusing unless you know to check
`tmux show-environment -g TMUX_PLUGIN_MANAGER_PATH` inside a live session.

Fixed by pinning the path explicitly in `tmux.conf`, before the `@plugin` lines
(TPM's own documented override):

```
set-environment -g TMUX_PLUGIN_MANAGER_PATH "$HOME/.tmux/plugins/"
```

`tmux-resurrect`/`tmux-continuum` were migrated from `~/.config/tmux/plugins/`
(repo-tracked, via stow) to `~/.tmux/plugins/` (outside the repo, matching
`install.sh`'s clone target) to match, and `systemd/tmux.service`'s
`ExecStop` was updated to the new `tmux-resurrect/scripts/save.sh` path.
Verified end-to-end with a live session: `TMUX_PLUGIN_MANAGER_PATH` now
resolves to `~/.tmux/plugins/`, `install_plugins.sh` finds all three plugins
already there without re-cloning, and `save.sh` runs cleanly from the new
location.

**Gotcha worth remembering**: adding a new unit file to an already-stowed package
doesn't retroactively symlink it — `stow` only acts when you run it. Found this
during a later stability pass: `~/.config/systemd/user/tmux.service` didn't exist
at all despite the repo's copy being correct, because `stow systemd` had last been
run before `tmux.service` existed in the package. Harmless as long as the unit
stays un-enabled, but `systemctl --user enable --now tmux.service` would fail
outright with "unit not found" until a `stow -R -t ~ systemd` fixes it. If you add
a file to an already-stowed package, restow it — don't assume the symlink appeared
on its own.

## The one true font: JetBrainsMono Nerd Font

Every config that renders text with icons — `kitty`, `tmux`, `sway` (window
title/border font), `mako`, `wofi`, `zed`, `waybar` — uses `"JetBrainsMono Nerd Font"`.
One font, one pacman package (`ttf-jetbrains-mono-nerd`), zero manual downloads. This
used to be `ZedMono Nerd Font`, a ~700MB manual download from its own upstream nerd-fonts
release with no package-manager equivalent; migrated everything off it (see
2026-08-23 in the changelog for the full story, including a real mistake made along
the way — the font directory got deleted before every reference to it had been found).
If you're about to add a new app to this setup and it wants a monospace/icon font,
use this one unless you have a specific reason not to — consistency here is what made
the tmux/waybar glyph debugging tractable in the first place.

## Known gaps that need root, not left silently unfixed

Two things identified during an optimization pass that this environment could not
apply itself (no `sudo` access here) — flagged explicitly rather than either faking a
fix or silently skipping them:

- **Unused display managers still installed on the live machine.** `packages/pacman.txt`
  no longer lists `greetd`, `greetd-tuigreet`, or `ly` (pruned so a *fresh* install
  won't carry them forward), but they're still actually installed on this machine.
  To remove them here too:

```bash
sudo systemctl disable greetd ly 2>/dev/null
sudo pacman -R greetd greetd-tuigreet ly
```

- **`systemd-networkd-wait-online.service` was eating ~2 minutes of every boot**,
  waiting for `wlan0` to become "routable" through `systemd-networkd` — which can
  never happen, because `NetworkManager` already owns that interface. Separately,
  `iwd.service` was enabled and running unused (NetworkManager's real wifi backend is
  `wpa_supplicant`). Fixed in `install.sh` (no longer enables `iwd` as a service — the
  package stays, for `iwctl`'s use bootstrapping Wi-Fi from a bare TTY). **Not yet
  fixed on the live machine** — needs `sudo`:

```bash
sudo systemctl disable --now iwd.service
sudo systemctl disable --now systemd-networkd-wait-online.service systemd-networkd.service
```

  `systemd-resolved` is genuinely in use (confirmed via `resolvectl status`) and
  should stay enabled — don't touch it while cleaning this up.
- **Docker can bypass UFW.** Docker manipulates `iptables` directly for published
  container ports (`-p`), which UFW's rules don't see. See
  **[docs/DOCKER_SECURITY.md](DOCKER_SECURITY.md)** for the full mechanism, what was
  actually checked on this machine (no live exposure as of the last check — nothing
  published), and a concrete two-layer fix: a zero-config habit (bind to `127.0.0.1`)
  plus `docs/harden-docker.sh` + `docs/docker-user-rules.service`, a `DOCKER-USER`-chain
  script for when you do need to publish something. Neither script is auto-run by
  `install.sh` or wired into any stow package — deliberately opt-in, since it changes
  network-filtering behavior and hasn't been tested against this system (no `sudo` in
  this session).

## A public docs site, and README.md fixing itself along the way

Asked directly: "i think we don't have a website for our repo create one with
github i guess there is some setup for it right." Confirmed there wasn't --
`gh api repos/.../pages` returned a plain 404, GitHub Pages was never enabled.

Checked `README.md` before building anything on top of it, since it was about to
become the site's actual homepage -- found it genuinely stale: its "Desktop
Stack" table and "Repository Structure" tree had no `mpd`/`rmpc` at all (the
whole termusic-replacement this session did), and the manual `stow` example in
Installation was missing them too. Fixed all three rather than build a public
site on top of known-wrong content.

Deliberately did **not** write a separate `docs/index.md` as the site's actual
homepage. GitHub Pages/Jekyll uses `README.md` as the homepage automatically
when there's no `index.md`/`index.html` at the source root -- and README.md was
already a genuinely complete "installation guide + documentation" page (Quick
Start, Features, Desktop Stack, Repository Structure, full Installation walk-
through, Managing Configurations, Local Configuration, Goals) once the stale
parts were fixed. A separate site-only copy would just be a second thing to
keep in sync with the real README forever -- one file, reused as-is, avoids that
entirely. `CHANGELOG.md` and `docs/*.md` are reachable from the same build for
the same reason (Pages sourced from the repo root, not a `/docs` subfolder --
`CHANGELOG.md` lives at the root, not inside `docs/`, so scoping the build to
`/docs` alone would have silently left it unreachable from the site).

Added one new file, `_config.yml` at the repo root: `theme: jekyll-theme-cayman`
(one of GitHub Pages' own built-in supported themes -- no Gemfile, no build
step beyond that one line, confirmed via pages.github.com/themes before
picking it, not guessed) plus an `exclude:` list for every actual dotfile
package directory (`sway/`, `waybar/`, `kitty/`, etc.) so Jekyll's build only
ever processes the real documentation, not several hundred unrelated config
files this repo also happens to contain.

**Did not take a live screenshot for the README's existing placeholder
section**, even though the tooling to do it was right there (`grim`, a real
running desktop matching everything documented). Checked what was actually on
screen first (`swaymsg -t get_tree`) and found a real browser window with a
personal email address in its title bar and a live ngrok tunnel URL, both part
of the user's actual live session -- a public GitHub Pages screenshot is a
published, hard-to-fully-reverse artifact once it's live and possibly indexed,
and there wasn't a way to fully vet or sanitize a live desktop capture (tmux
pane content, other window titles) well enough to publish it without asking
first. Left the existing honest placeholder in place instead of taking that
risk unprompted.

Enabled Pages via the API once the content actually existed on `main` (source:
`main` branch, path `/`, matching the branch this repo already treats as "the
public, stable state" — see `docs/VERSIONING.md`), then verified the real build
succeeded and the site was actually reachable (`curl` the resulting URL, not
just trusted the API call returning success) before considering this done.

## Renamed to Vayu, and a real custom dark hero-layout homepage

Direct follow-up, same evening: rename the repo to something from Hindu
mythology/history, make the site dark instead of light, and stop using the
stacked README-as-homepage layout for something with a name/tagline on the
left and a desktop image on the right instead.

**Name**: `arch_sway_setup` → `vayu`, after the Hindu god of wind. The fit is
direct, not decorative — Sway (the window manager this whole repo is built
around) tiles and rearranges windows constantly, the same way air moves, and
"sway" itself literally means to move that way. Renamed via `gh repo rename`,
then explicitly updated the local `origin` remote to the new URL and ran a
real `git fetch` through it to confirm the rename had actually propagated,
not just trusted the API response. Grepped the whole repo for the old name
(`arch_sway_setup`) to find every real reference rather than guess where it
might appear — found exactly two files (`install.sh`'s own curl one-liner
and `REPO_URL`; every GitHub/raw.githubusercontent link in `README.md`) and
updated both. Also set the repo's GitHub description and homepage URL to
match, and confirmed GitHub Pages carried the rename over automatically
(`gh api repos/.../pages` still resolved correctly at the new
`Theyashsawarkar/vayu` path immediately after).

**Homepage**: replaced the previous "Pages serves README.md automatically"
approach with a real, hand-written `index.html` at the repo root. Jekyll/
Pages' own precedence rule made this possible without extra config: an
`index.html` with no YAML front matter is served completely untouched
(static passthrough, no theme layout wrapping it) and always wins over
`README.md`/`index.md` as the site root when more than one exists — so the
custom homepage and the still-Jekyll-built doc pages (`CHANGELOG.html`,
`docs/ARCHITECTURE.html`, `docs/VERSIONING.html`) coexist in one build with
zero conflict.

**`README.md` itself is deliberately left as a raw passthrough, not a
Jekyll-built page** -- caught this live, not assumed: `README.html` 404'd
after the first deploy, traced it to the same "no front matter -> served
untouched" rule used deliberately for `index.html` above, this time
applying somewhere it wasn't wanted. The obvious fix (an empty `---\n---\n`
front-matter block, the standard Jekyll trick to force processing) was
tried and reverted after checking GitHub's *own* README renderer against it
first (`gh api repos/.../readme`) -- it doesn't strip front matter the way
Jekyll does, and rendered it as two literal `hr` elements at the very top
of the actual GitHub repo page, the single most-visible view of this
project. Not worth trading that for a themed mirror of a page nothing on
the site even links to (`index.html` links out to the GitHub-native README
directly, not a local copy) -- reverted, left `README.md` as a plain
passthrough (still fetchable at `/README.md` on the Pages site, just not
rendered as HTML there).

Layout follows the pattern asked for directly: a hero section with the name,
tagline, install snippet, and CTA buttons on the left, a real screenshot of
the actual desktop on the right — the specific split-hero pattern common to
project landing pages, even though it wasn't named as such in the request.
Below that, a feature grid and links out to the full docs. Colors are this
desktop's own Catppuccin Mocha values used directly (same hexes already in
`rmpc`'s theme, `waybar/style.css`), not a generic "dark theme" — the site
is meant to read as part of the same thing it's documenting. The *other*
pages (still Jekyll-built) switched from `jekyll-theme-cayman` (light) to
`jekyll-theme-slate` — one of GitHub Pages' own built-in themes, dark by
default — specifically so the whole site is consistently dark, not just the
new custom homepage while the doc pages stayed light underneath it.

**The screenshot took real care, not just running `grim` where things stood.**
Checked the actual window tree first (`swaymsg -t get_tree`) rather than
assume the screen was safe to capture: a browser window on another
workspace and a live tmux pane on the focused one, and since a floating
`rmpc` window doesn't cover the full 1920x1080 output, capturing it directly
where it was would have left that tmux pane visible in the margins around
it. Switched to a genuinely empty workspace, moved `rmpc` there via the
scratchpad, confirmed via the tree that it was the *only* node on that
workspace before capturing anything, then restored the original focused
workspace and hid `rmpc` back to the scratchpad afterward, leaving the real
session exactly as found. Resized and re-encoded the result (1920x1080 PNG
→ 1600x900 JPEG, ~230KB) rather than ship an untouched multi-megabyte
screenshot as a page asset.

Verified live the same way as the rest of this session's site work: pushed,
polled the Pages build API until it reported `"status":"built"` rather than
assuming a quick build had finished, then `curl`'d the actual homepage and
every linked doc page for real HTTP 200s and real content.

## The doc pages: a real layout, a sidebar TOC, and the Package map table gone

Direct feedback, same evening, pointed at the live `docs/ARCHITECTURE.html`
page specifically: "take a look at this optimize this ui and make it more
asthetic. instead of putting it in the table find other way to better
structure this page instead."

**The table really was a bad fit for its own content, not just visually
plain.** Reread it before changing anything: 20 rows, and their actual
description lengths ranged from a 6-character one-liner (`nvim` — "Editor")
to a single cell over 2,400 characters long (`bluetooth-picker.py`'s row,
genuinely several paragraphs of history and reasoning). A markdown table
forces every row into the same fixed column widths regardless — exactly
wrong for content this uneven, not something better CSS on the `table`
tag alone could fix.

**Replaced it with a responsive card grid + native `details` for the long
entries**, entirely inside `docs/ARCHITECTURE.md` itself (not a
site-only copy) so both the GitHub-native view and the Pages site benefit,
and there's still exactly one source of truth. Parsed the original table
with a small Python script rather than retype ~1,800 words of hard-won
documentation by hand — checked first that no row's content contained a
literal `|` that could confuse a naive split (`grep`-counted pipes per line,
all exactly 4, meaning exactly 3 columns, safe to split on) before trusting
the automated pass, then diffed the extracted text against what was
actually in the file to confirm nothing was corrupted or dropped. The five
genuinely long entries (`nwg-bar`, `docker-picker.py`,
`bluetooth-picker.py`, `networkmanager-dmenu`, `wifi-picker.py`) get a
hand-written one-line summary visible by default plus their full original
text, verbatim, inside a `details`; the other fifteen just show their
short description directly, no accordion needed for one sentence.
`markdown="1"` on the wrapping `div`/`details` tells kramdown to still
process the markdown inside a raw HTML block (backticks → real `code`,
`*emphasis*` → real `em`) — verified this actually worked by checking the
built page's real HTML output for `<code class="language-plaintext...">`
tags, not literal backtick characters.

**Added a real custom layout (`_layouts/docs.html`) instead of relying on
the built-in Jekyll theme any further** — a sidebar table of contents (built
by `assets/docs.js` from whatever `h2` elements are actually on the page
at build/view time, not a hand-maintained list that would drift out of sync
with a 3,500-line, 58-section document) with scroll-based active-section
highlighting via `IntersectionObserver`, and the same Catppuccin Mocha
variables already used on the homepage (`assets/style.css`) extended into
`assets/docs.css` for consistent typography, code blocks, and the new
package cards — one palette across the whole site, not the homepage looking
different from everything else in it.

**How the layout gets applied without ever touching the source files'
own front matter** — the same GitHub-native-rendering constraint already
hit once for `README.md` applies here too: `docs/ARCHITECTURE.md`,
`docs/VERSIONING.md`, and `CHANGELOG.md` are all read directly on GitHub
(linked straight from `README.md`), and adding a `---` front-matter block
to any of them would show up as literal horizontal rules on the actual
GitHub page, the same regression already caught and reverted once for
`README.md`. Used `_config.yml`'s `defaults:` key instead — `scope: {path:
"docs/ARCHITECTURE.md"}` with `values: {layout: "docs", title:
"Architecture"}`, one block per file — which assigns a layout and title by
path with **zero change to the source file itself**. Worth noting since it
wasn't obvious going in: these three files were already building into real
`.html` pages even *before* this, with no front matter and no `defaults:`
entry at all (confirmed live earlier this session) — unlike `README.md`,
which Jekyll appears to specifically exclude from conversion by filename
convention. `defaults:` only had to solve "assign the right layout/title",
never "make these files build at all".

Considered, then discarded, a more complex alternative first: thin wrapper
pages (`pages/architecture.md` etc.) with real front matter, transcluding
the actual file's content via Liquid's `include_relative` tag piped
through the `markdownify` filter. Built and even started testing this
before realizing `defaults:` solved the exact same problem with no new
files, no transclusion indirection, and no risk of the included copy
ever silently drifting from what the real source file actually says —
deleted it once `defaults:` was confirmed working live.

Verified all of this the same way as everything else on this site: pushed
straight to `main` specifically to get a real Pages build to test against
(this was itself the verification step, not a separate "trust the config"
pass), polled for `"status":"built"`, then pulled the real built HTML for
all three doc pages and grepped it directly — confirmed each page's real
`title` tag correctly read "Architecture | Vayu" etc. (the per-file `defaults:` title actually applied),
`docs-layout`/`docs-sidebar`/`pkg-card` present in the real output (not just
written in the source), all 20 package cards accounted for, and the
markdown-inside-`details` processing working correctly by finding real
`code`/`em` tags in the built page rather than literal markdown
characters.

## docs/KEYBINDINGS.md, a hero redesign, and the real lesson from a much deeper kramdown bug

Direct feedback, several parts at once: fix real bugs on the CHANGELOG page,
add a keybindings page with its own nav entry, fix a pixelated music-player
thumbnail, add copy buttons, redesign the hero (multiple screenshots, a
scroll-driven rotation, a much shorter tagline), and clean up the header and
feature grid.

**docs/KEYBINDINGS.md** is generated from the same real parsing
`scripts/.local/bin/keybind-search.py` already does live (real `bindsym`/
`bind` lines from `sway/config`/`tmux.conf`, paired with their own
comments/`-N` notes) -- not a hand-maintained list kept separately from the
configs that actually define the bindings, which would inevitably drift.
Scoped to Sway's full 94 bindings plus Tmux's ~22 *custom* ones (not all
~260 including stock defaults -- those are generic tmux knowledge, not
anything specific to this setup).

**music-search.py's thumbnail pixelation**: `mqdefault.jpg` (320x180) to
`hqdefault.jpg` (480x360) -- confirmed the larger tier is reliably available
at the same fixed, unsigned URL shape before switching (curl'd it directly),
and measured the real cost (10 concurrent fetches: ~0.4s to ~0.5s) rather
than asserting "still fast" unchecked.

**The real lesson from this session's deepest kramdown investigation**:
fixing the CHANGELOG page's broken rendering took eight separate, genuine
wrong turns before landing on the actual fix (full blow-by-blow in
`CHANGELOG.md`'s own entry for this date) -- worth pulling out the single
reusable lesson here, since it'll matter again the next time a code fence or
inline code span looks broken on this site: **kramdown's HTML-tag detection
appears to run before backtick code-span content is fully isolated from the
rest of the document.** A word wrapped in angle brackets, anywhere in the
raw source -- even inside backticks, even describing something totally
unrelated to HTML (a placeholder such as the word file wrapped that way, a
Rust generic type parameter, a keybind notation like rmpc's own Escape-key
entry syntax) -- gets provisionally treated as a possible opening HTML tag.
If no matching closing tag exists anywhere later in the document, kramdown
appears to stop processing markdown syntax entirely from that point to
end-of-file, rather than failing loudly or falling back gracefully
per-paragraph. GitHub's own CommonMark-based renderer doesn't have this
problem at all, which is exactly why a page can read perfectly on GitHub
natively while being silently, catastrophically broken on the Jekyll-built
site -- the two renderers are not just "mostly the same, kramdown is
stricter," they disagree on a genuinely load-bearing point.

**Practical rule going forward, for any future prose in a file this site
builds** (`CHANGELOG.md`, `docs/*.md` under a `defaults:` scope, *not*
`README.md`, which isn't Jekyll-built at all): never wrap a bare word in
angle brackets, backticks or not, unless it's genuine, real,
matched-open-and-closed HTML within the same short span (like this site's
own package-card markup, or a self-contained Pango markup example showing
a sized icon span with its own matching close right there -- confirmed safe
specifically *because*
the close tag is right there in the same span, not because backticks
protected it). For a real placeholder, just don't decorate it with brackets
at all (`file`, `name`, `pid` reads fine on its own, especially already
inside backtick code styling). For something that specifically needs to
*show* a literal angle bracket as part of real syntax being quoted (a
generic type, a keybind notation, literal HTML being described), reword
around it in plain English rather than reach for entity-encoding or
backslash-escaping -- both were tried here and both produced their own new,
different, real cosmetic bugs (entities get double-escaped by a working
code-span's own auto-escaping; backslash escapes aren't processed inside
code spans per the CommonMark spec at all, so the backslash itself stays
visible).

## music-search.py: play by default (mpv), download moved to a flag

`music-search.py`'s Enter action used to be "download an mp3 into
~/Music", full stop -- the only thing it was ever built to do. Asked for
a real change: Mod+Shift+Y's Enter should play the picked result
immediately, with a way to choose audio-only vs. a real video window,
and the old download-to-library behavior should still exist somewhere
rather than being deleted.

**Player choice**: mpv, not MPD/rmpc. MPD's whole design center is a
curated, persistent local library (that's what rmpc's own card above is
for) -- repurposing it for "stream this one URL right now, don't add it
to anything" would fight its actual job. mpv is built for exactly this:
it ships a `ytdl_hook.lua` that resolves and plays a YouTube URL directly
with zero extra plumbing, confirmed live with nothing more than
`mpv <url>`, and it's already installed (v0.41.0) with no dotfiles
config of its own before this. One binary covers both modes needed here
(`--no-video --ytdl-format=bestaudio` for audio-only, `--force-window=yes`
for real video) instead of reaching for a second tool.

**Verification, not just "it launched"**: a live process staying alive
isn't proof of playback -- confirmed via mpv's own JSON IPC socket
(`--input-ipc-server`), querying `time-pos` twice a few seconds apart and
watching it actually advance, for both audio and video. Video specifically
was also confirmed via `swaymsg -t get_tree` mid-playback: real app_id
`mpv` (lowercase, confirmed rather than assumed from the binary name),
floating, `1280x722` (the requested `1280 720` plus mpv's own window
decoration), centered. The whole play path was driven through the actual
sway keybinding's real code path too, not just raw mpv calls in
isolation -- `wtype` simulated real keystrokes into the live wofi popups
(search query, then picking a result) so the exact command music-search.py
itself constructs was what got verified, args and all.

**A real bug caught in that verification**: mpv/yt-dlp's own "best"
format selection picks whatever the highest resolution available is with
zero regard for whether the machine can actually decode it smoothly --
dropped-frame count climbed continuously through a live 4K test result.
Video mode now explicitly caps at 1080p
(`bestvideo[height<=?1080]+bestaudio/best[height<=?1080]`) instead of
trusting the untouched default.

**Mode toggle**: `media-play-mode.sh` (Mod+Ctrl+Y), same persisted-state-file
pattern as `notification-mode.sh`/`theme-toggle.sh` -- a plain file under
`~/.local/state/`, not anything transient, since it has to be readable by
whatever separate `music-search.py` invocation runs next, possibly long
after the toggle itself ran. `music-search.py` reads it fresh on every
run (no caching), and echoes the active mode straight into the wofi
search prompt itself ("Search YouTube (audio)..." / "(video)...") so
which mode is active is never a guess at the point it actually matters.

**Download preserved, not removed**: `--download` (Mod+Shift+Ctrl+Y)
reuses every bit of the existing search/pick code and does exactly what
this script always did -- confirmed with a real end-to-end download
through the same `wtype`-driven flow, a real mp3 landed in `~/Music` with
its thumbnail cleaned up afterward same as before, then removed as
test-only output afterward.

**for_window rule**: mpv's video window gets `floating enable, resize set
1280 720, move position center` -- a utility popup like rmpc gets, minus
rmpc's blur/scratchpad treatment, since this is meant to be watched
immediately, not tucked away and toggled back into view later.
