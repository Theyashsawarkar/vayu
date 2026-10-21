# Keybindings

The live, always-complete list is **`Super+Shift+/`** (every source below, in
[mudra](https://github.com/Theyashsawarkar/mudra), a Vyom tool: search by what a key does, Enter runs it) and, inside tmux, **`Ctrl+a ?`** (tmux keys; Enter runs the picked
binding). Both come from `scripts/.local/bin/keybind-search.py`, which re-reads the
real configs every time: sway (`#:` line above each `bindsym`), tmux (`bind -N`
notes, stock keys marked `default`), kitty (`#:` above each `map`), Zed
(`keymap.json`), nāda and the Vyom tools (`# keybind:` lines in their packages), and keys that exist only inside popup scripts
(`# keybind:` lines). `keybind-search.py --check` fails if any binding is
undescribed. Every description reads **action + object**, so search the same
way: `kill window`, `open lazygit`, `raise volume`, `take screenshot` (the search
box's placeholder says so too). See `CLAUDE.md` for the annotation rules. This page is the
hand-written overview of the main ones.

`Super` is the Windows/Cmd key (sway's `$mod`).

## Sway

### Popups & pickers (Vyom)

Every panel is a [Vyom](https://github.com/Theyashsawarkar/vyom) tool, each in its own repo. The same key again closes it. Inside any panel: type to search, <kbd>Up</kbd>/<kbd>Down</kbd> move, <kbd>Enter</kbd> runs, <kbd>Tab</kbd> jumps to the next tool, <kbd>Esc</kbd> closes; each tool's own keys are in its footer (and in <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>/</kbd>).

- <kbd>Super</kbd>+<kbd>d</kbd> — Apps ([dvara](https://github.com/Theyashsawarkar/dvara)): your frequent apps first, app actions on <kbd>Ctrl</kbd>+<kbd>1</kbd>…, <kbd>Shift</kbd>+<kbd>Enter</kbd> runs what you typed
- <kbd>Super</kbd>+<kbd>c</kbd> — Calculator ([ganit](https://github.com/Theyashsawarkar/ganit)): answers as you type (units, currency, %), <kbd>Enter</kbd> copies
- <kbd>Super</kbd>+<kbd>m</kbd> — Clipboard ([smriti](https://github.com/Theyashsawarkar/smriti)): links, images, code told apart; <kbd>Ctrl</kbd>+<kbd>Enter</kbd> pastes, <kbd>Ctrl</kbd>+<kbd>P</kbd> pins, <kbd>Delete</kbd> deletes
- <kbd>Super</kbd>+<kbd>.</kbd> — Emoji ([bhava](https://github.com/Theyashsawarkar/bhava)): <kbd>Enter</kbd> types it into the window you were in, <kbd>Ctrl</kbd>+<kbd>T</kbd> skin tone
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>w</kbd> — Wi‑Fi ([tarang](https://github.com/Theyashsawarkar/tarang)): connect (password typed inline), <kbd>Ctrl</kbd>+<kbd>D</kbd> disconnect, <kbd>Ctrl</kbd>+<kbd>H</kbd> hotspot tab with a QR code
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>b</kbd> — Bluetooth ([setu](https://github.com/Theyashsawarkar/setu)): devices with battery, <kbd>Enter</kbd> connects / pairs
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>o</kbd> — Phone ([doot](https://github.com/Theyashsawarkar/doot), KDE Connect): send clipboard or a file, ring, browse
- <kbd>Super</kbd>+<kbd>Ctrl</kbd>+<kbd>a</kbd> — Stop the laptop ringing (phone's Find my device), otherwise pick an action on the current notification (Accept/Reject pairing, Undo phone clipboard, Show received file in folder)
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>d</kbd> — Docker ([patra](https://github.com/Theyashsawarkar/patra)): <kbd>Enter</kbd> logs, <kbd>Ctrl</kbd>+<kbd>R</kbd> restart, <kbd>Ctrl</kbd>+<kbd>S</kbd> stop/start, <kbd>Ctrl</kbd>+<kbd>T</kbd> shell
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>n</kbd> — Notifications ([suchana](https://github.com/Theyashsawarkar/suchana)): what's on screen with its actions, the history, do not disturb
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>p</kbd> — Power ([vishram](https://github.com/Theyashsawarkar/vishram)): <kbd>L</kbd> lock, <kbd>S</kbd> suspend, <kbd>E</kbd> log out, <kbd>R</kbd> reboot, <kbd>P</kbd> power off (5 s countdown, <kbd>Esc</kbd> cancels)
- <kbd>Super</kbd>+<kbd>q</kbd> — Quick settings ([kendra](https://github.com/Theyashsawarkar/kendra); also the ⚙ on the bar): Wi‑Fi, Bluetooth, hotspot, do not disturb, caffeine, dark theme, wallpaper, power profile, volume and brightness, lock and power
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>m</kbd> — [nāda](https://github.com/Theyashsawarkar/nada) (music player), toggle open/hidden
- <kbd>Super</kbd>+<kbd>Alt</kbd>+<kbd>Space</kbd> / <kbd>.</kbd> / <kbd>,</kbd> — music play/pause, next, previous (without opening nāda)
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>y</kbd> / <kbd>Super</kbd>+<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>y</kbd> — YouTube ([raga](https://github.com/Theyashsawarkar/raga)): search, play as video (mpv) / music (nāda); <kbd>Shift</kbd>+<kbd>Enter</kbd> the other way
- <kbd>Super</kbd>+<kbd>n</kbd> — Cycle notification mode (normal → silent → dnd)
- <kbd>Super</kbd>+<kbd>Ctrl</kbd>+<kbd>n</kbd> / <kbd>s</kbd> / <kbd>d</kbd> — Jump directly to normal / silent / dnd
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>/</kbd> — Keybindings ([mudra](https://github.com/Theyashsawarkar/mudra)): every binding by what it does, real key caps, <kbd>Enter</kbd> runs it
- The battery capsule on the bar — Battery ([urja](https://github.com/Theyashsawarkar/urja)): charge, time left, health, power profile, the charge-limit reminder

### Launch & session

- <kbd>Super</kbd>+<kbd>Return</kbd> — Open a terminal
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>q</kbd> — Kill focused window
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>c</kbd> — Reload sway config
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>e</kbd> — Exit sway (confirmation prompt)

### Focus & move windows

- <kbd>Super</kbd>+<kbd>h</kbd>/<kbd>j</kbd>/<kbd>k</kbd>/<kbd>l</kbd> or arrows — Move focus left/down/up/right
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>h</kbd>/<kbd>j</kbd>/<kbd>k</kbd>/<kbd>l</kbd> or arrows — Move the focused window left/down/up/right

### Workspaces

- <kbd>Super</kbd>+<kbd>1</kbd>..<kbd>0</kbd> — Switch to workspace 1–10
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>1</kbd>..<kbd>0</kbd> — Move focused window to workspace 1–10

### Layout

- <kbd>Super</kbd>+<kbd>v</kbd> / <kbd>Super</kbd>+<kbd>b</kbd> — Split horizontal / vertical
- <kbd>Super</kbd>+<kbd>s</kbd> — Stacking layout
- <kbd>Super</kbd>+<kbd>w</kbd> — Tabbed layout
- <kbd>Super</kbd>+<kbd>e</kbd> — Toggle split/tabbed
- <kbd>Super</kbd>+<kbd>f</kbd> — Fullscreen
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>Space</kbd> — Toggle floating
- <kbd>Super</kbd>+<kbd>Space</kbd> — Toggle focus tiling/floating
- <kbd>Super</kbd>+<kbd>a</kbd> — Focus parent container

### Scratchpad

- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>-</kbd> — Move focused window to scratchpad
- <kbd>Super</kbd>+<kbd>-</kbd> — Show/hide next scratchpad window

### Resize mode

- <kbd>Super</kbd>+<kbd>Ctrl</kbd>+<kbd>r</kbd> — Enter resize mode
- <kbd>h</kbd>/<kbd>j</kbd>/<kbd>k</kbd>/<kbd>l</kbd> or arrows (in resize mode) — Shrink/grow width or height
- <kbd>Return</kbd> / <kbd>Escape</kbd> (in resize mode) — Exit resize mode

### Screen recording

- <kbd>Super</kbd>+<kbd>r</kbd> — Record full screen
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>r</kbd> — Record a selected region
- <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>Space</kbd> — Record full screen (press again to stop)

### Media & hardware keys

- Volume Mute / Up / Down — Adjust volume (with on-screen indicator)
- Mic Mute — Toggle microphone mute
- Play/Pause, Prev, Next, Stop — Media playback control (`playerctl`)
- Brightness Up / Down — Adjust screen brightness (with on-screen indicator)

### Screenshots & lock

- <kbd>Print</kbd> — Screenshot, full screen
- <kbd>Super</kbd>+<kbd>Print</kbd> — Screenshot, select a region
- <kbd>Alt</kbd>+<kbd>Space</kbd> — Screenshot, full screen
- <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>;</kbd> — Lock screen

## Tmux

Prefix key is <kbd>Ctrl</kbd>+<kbd>a</kbd> (not tmux's default <kbd>Ctrl</kbd>+<kbd>b</kbd>). Every stock tmux
binding still works too -- this is only the set this repo added; the full list (~210 entries
including every stock default and the vi copy-mode keys) is `Ctrl+a ?` or `Super+Shift+/`.

- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Ctrl</kbd>+<kbd>a</kbd> — Send a literal Ctrl-a to the application
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>\</kbd> — Split horizontally (side by side), in the current pane's directory
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>-</kbd> — Split vertically, in the current pane's directory
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>c</kbd> — New window, in the current pane's directory
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>&lt;</kbd>/<kbd>&gt;</kbd> — Swap window left/right
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>r</kbd> — Reload tmux config (mako notification only)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>?</kbd> — Search tmux keybindings; <kbd>Enter</kbd> runs the picked one
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>:</kbd> — Floating command prompt (runs in the real client, never nests)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>s</kbd> — Session picker with live previews (<kbd>Enter</kbd> switches, <kbd>Ctrl</kbd>+<kbd>x</kbd> kills, <kbd>Ctrl</kbd>+<kbd>n</kbd> or a new name + <kbd>Enter</kbd> creates, <kbd>Esc</kbd> closes)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>w</kbd> — Classic session/window tree
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>b</kbd> — Last session
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>,</kbd> / <kbd>R</kbd> — Rename window (floating input, prefilled)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>$</kbd> — Rename session (floating input, prefilled)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>x</kbd> / <kbd>&amp;</kbd> — Kill pane / window (centred confirm menu)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>X</kbd> — Kill current session, hopping to the next one (confirm menu)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Alt</kbd>+<kbd>k</kbd> — Kill every other session (confirm menu)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Ctrl</kbd>+<kbd>s</kbd> / <kbd>Ctrl</kbd>+<kbd>r</kbd> — Save / restore sessions (tmux-resurrect, mako notification only)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>g</kbd> — lazygit popup in the current directory
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>G</kbd> — Pull requests popup ([sangam](https://github.com/Theyashsawarkar/sangam), its own repo; also the `sangam` command in any terminal), from any folder: sections like gh-dash (review requested, my PRs, pinned repos from `~/.config/gh-pr/sections`, plus the repo you're in), each searched as its own GitHub account; read, review, merge and close PRs without the browser. Vim-style: <kbd>j</kbd>/<kbd>k</kbd> move, <kbd>h</kbd>/<kbd>l</kbd> section, <kbd>f</kbd> open/merged/closed/all (<kbd>F</kbd> open ↔ all), <kbd>u</kbd> switch account, <kbd>s</kbd> search GitHub (author:x, label:y…), <kbd>S</kbd> add / edit / delete / move sections (or pin the repo you're in), <kbd>E</kbd> the sections file, <kbd>1</kbd>–<kbd>4</kbd> overview/diff/checks/comments, <kbd>Enter</kbd> full screen (failed check logs in checks), <kbd>/</kbd> search, <kbd>m</kbd> merge, <kbd>a</kbd> approve, <kbd>r</kbd> request changes, <kbd>c</kbd> comment, <kbd>x</kbd> close/reopen, <kbd>o</kbd> checkout, <kbd>d</kbd> draft/ready, <kbd>q</kbd> or <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>G</kbd> closes it; <kbd>?</kbd> inside it opens a key popup
- Click the **"N to review"** capsule on the tmux bar — the same pull requests popup (sangam); a click on a window capsule still selects that window
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>a</kbd> — jump to the Claude session that has waited longest for you (finished its turn or asks for permission, in another pane); clicking the **"N waiting"** capsule does the same
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>C</kbd> — Claude Code accounts ([vesha](https://github.com/Theyashsawarkar/vesha)); the bar's **"account N%"** capsule shows the active one and its 5-hour usage
- Click a port in the **"󰒋 :3000"** capsule — opens that dev server in the browser
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>t</kbd> — Scratch shell popup (<kbd>Ctrl</kbd>+<kbd>d</kbd> closes)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>T</kbd> — btop popup
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Tab</kbd> — extrakto: fuzzy-pick paths/URLs/words from the pane
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>S</kbd> — Toggle synchronized input to all panes
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>z</kbd> — Toggle pane zoom
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>h</kbd>/<kbd>j</kbd>/<kbd>k</kbd>/<kbd>l</kbd> — Move focus to the pane left/below/above/right (vim-style)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>n</kbd> / <kbd>p</kbd> — Switch to the next / previous window (wraps around)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Shift</kbd>+<kbd>h</kbd>/<kbd>j</kbd>/<kbd>k</kbd>/<kbd>l</kbd> — Resize pane left/down/up/right (5 columns / 2 rows; repeats without the prefix)
- <kbd>Alt</kbd>+<kbd>Left</kbd>/<kbd>Right</kbd>/<kbd>Up</kbd>/<kbd>Down</kbd> — Move focus between panes (no prefix needed)
- <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>Left</kbd>/<kbd>Right</kbd> — Resize pane left/right by 5
- <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>Up</kbd>/<kbd>Down</kbd> — Resize pane up/down by 2
- <kbd>Alt</kbd>+<kbd>1</kbd>..<kbd>9</kbd> — Select window 1–9 (no prefix needed; a missing window is a silent no-op)
- <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>1</kbd>..<kbd>6</kbd> — Select window 1–6 (no prefix needed, kitty extended keys)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Enter</kbd> — Enter copy mode (the session capsule turns green)
- <kbd>v</kbd> (in copy mode) — Begin visual selection
- <kbd>Esc</kbd> / <kbd>q</kbd> (in copy mode) — Leave copy mode
- <kbd>Ctrl</kbd>+<kbd>v</kbd> (in copy mode) — Toggle rectangle/block selection
- <kbd>y</kbd> (in copy mode) — Copy selection to the Wayland clipboard (`wl-copy`)
- Mouse — drag copies and keeps the highlight (click clears it); double-click copies a word, triple-click a line, in or out of copy mode
