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

## The Space grammar (every tool)

Every tool we make is moving to the same vim-style keys (the plan:
`~/Documents/mockups/vim-keys-roadmap.html`). **Normal** mode is where keys are
commands and typing changes nothing; **Insert** is where typing goes into a field
(search boxes, editors); <kbd>Esc</kbd> goes from Insert to Normal, and in Normal
backs out step by step until the tool closes. In Normal, <kbd>Space</kbd> is the
**leader**: after it, a letter names a group that means the same in every tool,
and a menu of the next keys (which-key) appears if you wait.

- Direct keys: <kbd>j</kbd>/<kbd>k</kbd> move (counts: <kbd>5j</kbd>), <kbd>H</kbd>/<kbd>L</kbd> previous / next tab, <kbd>g</kbd><kbd>g</kbd>/<kbd>G</kbd> first / last, <kbd>Ctrl</kbd>+<kbd>d</kbd>/<kbd>u</kbd> half a page, <kbd>/</kbd> search, <kbd>Enter</kbd> the main action, <kbd>o</kbd> open, <kbd>i</kbd>/<kbd>a</kbd> type, <kbd>y</kbd><kbd>y</kbd> copy, <kbd>d</kbd><kbd>d</kbd> delete (asks: <kbd>y</kbd> yes, any other key no), <kbd>r</kbd> refresh, <kbd>q</kbd> back / close, <kbd>?</kbd> every key.
- Reserved leader groups: <kbd>Space</kbd> <kbd>Space</kbd> palette · <kbd>?</kbd> every key · <kbd>q</kbd> close · <kbd>t</kbd> tabs · <kbd>u</kbd> UI toggles (<kbd>u</kbd> <kbd>f</kbd> fullscreen) · <kbd>y</kbd> copy · <kbd>f</kbd> find / filter · <kbd>s</kbd> sort · <kbd>r</kbd> refresh · <kbd>a</kbd> add / new · <kbd>d</kbd> delete · <kbd>e</kbd> edit · <kbd>o</kbd> open outside · <kbd>g</kbd> go to · <kbd>m</kbd> mark · <kbd>,</kbd> settings · <kbd>k</kbd> ask the AI. The other letters (b c h i j l n p v w x z) are each tool's own nouns.
- Space never toggles or plays anything in Normal mode, and no single key does something you can't take back.

How a tool says it (`# keybind:` lines, see `CLAUDE.md`): the mode after the scope,
`# keybind: Vyom/ganit calculator:normal | Space y y | Copy the answer`, and a group's
name in `# keybind-group: Vyom/ganit | Space y | Copy`. `keybind-search.py --list
--keys "space y"` lists one group; `--groups` every group; `--check` warns when a
tool breaks the grammar (a reserved group used for something else, `g` beside
`g g` in one mode, a capital in the notes that the code never checks, one key
that deletes or locks), and fails on it with `--strict`. mudra
(<kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>/</kbd>) shows the mode and leader chips,
finds `space y` as a sequence, and has a Leader tab with every tool's tree.

## Sway

### Popups & pickers (Vyom)

Every panel is a [Vyom](https://github.com/Theyashsawarkar/vyom) tool, each in its own repo. The same key again closes it. Inside any panel: type to search, <kbd>Up</kbd>/<kbd>Down</kbd> move, <kbd>Enter</kbd> runs, <kbd>Ctrl</kbd>+<kbd>K</kbd>/<kbd>J</kbd> move too, <kbd>Tab</kbd> / <kbd>Shift</kbd>+<kbd>Tab</kbd> jump to the next / previous tool, <kbd>Esc</kbd> closes. A tool with tabs (Calculate/Convert, clipboard kinds, emoji categories, keybinding apps...) shows each tab's number and switches them the same way everywhere: <kbd>Ctrl</kbd>+<kbd>Tab</kbd> / <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>Tab</kbd> (or <kbd>Ctrl</kbd>+<kbd>H</kbd>/<kbd>L</kbd>) next/previous, <kbd>Ctrl</kbd>+<kbd>1</kbd>…<kbd>9</kbd> the numbered one (nāda's tabs too); each tool's own keys are in its footer (and in <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>/</kbd>).

- <kbd>Super</kbd>+<kbd>d</kbd> — Apps ([dvara](https://github.com/Theyashsawarkar/dvara)): your frequent apps first, app actions on <kbd>Ctrl</kbd>+<kbd>1</kbd>…, <kbd>Shift</kbd>+<kbd>Enter</kbd> runs what you typed
- <kbd>Super</kbd>+<kbd>c</kbd> — Calculator ([ganit](https://github.com/Theyashsawarkar/ganit)): answers as you type (units, currency, %) with how it read them, <kbd>Enter</kbd> copies, <kbd>Alt</kbd>+<kbd>1</kbd>…<kbd>4</kbd> other forms; its Convert tab (<kbd>Ctrl</kbd>+<kbd>Tab</kbd>) shows an amount in every pinned currency or unit
- <kbd>Super</kbd>+<kbd>m</kbd> — Clipboard ([smriti](https://github.com/Theyashsawarkar/smriti)): links, images, code told apart; <kbd>Ctrl</kbd>+<kbd>Enter</kbd> pastes, <kbd>Ctrl</kbd>+<kbd>P</kbd> pins, <kbd>Delete</kbd> deletes
- <kbd>Super</kbd>+<kbd>.</kbd> — Emoji ([bhava](https://github.com/Theyashsawarkar/bhava)): <kbd>Enter</kbd> types it into the window you were in, <kbd>Ctrl</kbd>+<kbd>T</kbd> skin tone
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>w</kbd> — Wi‑Fi ([tarang](https://github.com/Theyashsawarkar/tarang)): connect (password typed inline), <kbd>Ctrl</kbd>+<kbd>D</kbd> disconnect, the Hotspot tab (<kbd>Ctrl</kbd>+<kbd>L</kbd>) with a QR code
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>b</kbd> — Bluetooth ([setu](https://github.com/Theyashsawarkar/setu)): devices with battery, <kbd>Enter</kbd> connects / pairs
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>o</kbd> — Phone ([doot](https://github.com/Theyashsawarkar/doot), KDE Connect): send clipboard or a file, ring, browse
- <kbd>Super</kbd>+<kbd>o</kbd> — Phone and laptop ([ekatva](https://github.com/Theyashsawarkar/ekatva)): the window with your phones, the action log, caffeine (keys inside it: `?`)
- <kbd>Super</kbd>+<kbd>Ctrl</kbd>+<kbd>o</kbd> — Pair a phone with ekatva (QR code, works from any network)
- <kbd>Super</kbd>+<kbd>Ctrl</kbd>+<kbd>a</kbd> — Stop the laptop ringing (phone's Find my device), otherwise pick an action on the current notification (Accept/Reject pairing, Undo phone clipboard, Show received file in folder)
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>d</kbd> — Docker ([patra](https://github.com/Theyashsawarkar/patra)): <kbd>Enter</kbd> logs, <kbd>Ctrl</kbd>+<kbd>R</kbd> restart, <kbd>Ctrl</kbd>+<kbd>S</kbd> stop/start, <kbd>Ctrl</kbd>+<kbd>T</kbd> shell
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>n</kbd> — Notifications ([akashvani](https://github.com/Theyashsawarkar/akashvani)): what's on screen with its actions, the history, do not disturb
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>p</kbd> — Power ([vishram](https://github.com/Theyashsawarkar/vishram)): <kbd>L</kbd> lock, <kbd>S</kbd> suspend, <kbd>E</kbd> log out, <kbd>R</kbd> reboot, <kbd>P</kbd> power off (5 s countdown, <kbd>Esc</kbd> cancels)
- <kbd>Super</kbd>+<kbd>q</kbd> — Quick settings ([kendra](https://github.com/Theyashsawarkar/kendra); also the ⚙ on the bar): Wi‑Fi, Bluetooth, hotspot, do not disturb, caffeine, dark theme, wallpaper, power profile, volume and brightness, lock and power
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>m</kbd> — [nāda](https://github.com/Theyashsawarkar/nada) (music player), toggle open/hidden
- <kbd>Super</kbd>+<kbd>y</kbd> — [drishya](https://github.com/Theyashsawarkar/drishya) (video player: YouTube, your videos, any stream link), toggle open/hidden; inside, <kbd>?</kbd> lists its keys
- <kbd>Super</kbd>+<kbd>Alt</kbd>+<kbd>Space</kbd> / <kbd>.</kbd> / <kbd>,</kbd> — music play/pause, next, previous (without opening nāda)
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

- <kbd>Super</kbd>+<kbd>r</kbd> — Record full screen (press again to stop)
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>r</kbd> — Record a selected region (press again to stop)

With system sound, saved to `~/Videos/recordings/`; the bar shows
`● REC` and a timer meanwhile (click it to stop), and the file is copied
when it stops.

### Media & hardware keys

- Volume Mute / Up / Down — Adjust volume (with on-screen indicator)
- Mic Mute — Toggle microphone mute
- Play/Pause, Prev, Next, Stop — Media playback control (`playerctl`)
- Brightness Up / Down — Adjust screen brightness (with on-screen indicator)

### Typing

- <kbd>Shift</kbd>+<kbd>Esc</kbd> — `~` (for 60% keyboards, whose `` ` ``/`~` shares the Esc key; on every keyboard, from Vayu's keymap `sway/.config/sway/xkb/vayu.xkb`)

### Screenshots & lock

- <kbd>Super</kbd>+<kbd>s</kbd> — Screenshot, full screen
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>s</kbd> — Screenshot, select a region
- <kbd>Super</kbd>+<kbd>Escape</kbd> — Lock screen

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
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Space</kbd> — The launcher: every tool by group, which-key style (type the letters straight through, or wait 0.25 s for the menu). <kbd>g</kbd> go to (<kbd>s</kbd> sessions, <kbd>l</kbd> last session, <kbd>w</kbd> tree, <kbd>c</kbd> waiting Claude), <kbd>c</kbd> Claude (<kbd>a</kbd> accounts, <kbd>s</kbd> skills, <kbd>w</kbd> waiting), <kbd>v</kbd> version control (<kbd>g</kbd> lazygit, <kbd>p</kbd> pull requests), <kbd>n</kbd> messages (<kbd>m</kbd> mail, <kbd>c</kbd> chat, <kbd>w</kbd> WhatsApp, <kbd>p</kbd> posts), <kbd>x</kbd> system (<kbd>p</kbd> ports, <kbd>d</kbd> Docker, <kbd>t</kbd> btop), <kbd>o</kbd> open (<kbd>t</kbd> scratch shell, <kbd>v</kbd> darshan, <kbd>e</kbd> editor), <kbd>u</kbd> toggles (<kbd>z</kbd> zoom, <kbd>s</kbd> sync panes), <kbd>t</kbd> windows (<kbd>n</kbd> new, <kbd>r</kbd> rename, <kbd>1</kbd>–<kbd>9</kbd>), <kbd>r</kbd> reload, <kbd>q</kbd> kill pane, <kbd>Space</kbd> search these keys. Every direct key below still works; tmux's old <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Space</kbd> (next layout) is gone, layouts stay on <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Alt</kbd>+<kbd>1</kbd>..<kbd>7</kbd>
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>?</kbd> — Search tmux keybindings; <kbd>Enter</kbd> runs the picked one (starts typing; <kbd>Esc</kbd> to Normal: <kbd>j</kbd>/<kbd>k</kbd>, <kbd>g</kbd><kbd>g</kbd>/<kbd>G</kbd>, <kbd>q</kbd>; <kbd>Esc</kbd> again closes)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>:</kbd> — Floating command prompt (runs in the real client, never nests)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>s</kbd> — Session picker with live previews (<kbd>Enter</kbd> switches, <kbd>Ctrl</kbd>+<kbd>n</kbd> or a new name + <kbd>Enter</kbd> creates; <kbd>Esc</kbd> to Normal, where <kbd>d</kbd><kbd>d</kbd> kills, and <kbd>Esc</kbd> again closes; <kbd>Ctrl</kbd>+<kbd>x</kbd> kills too; both ask first, <kbd>y</kbd> kills)
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
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>e</kbd> — Mail and chat popup ([narada](https://github.com/Theyashsawarkar/narada), its own repo; also the `narada` command in any terminal): Gmail sections (Inbox, Today, Unread, Starred, saved searches) and Google Chat spaces and DMs, one <kbd>Tab</kbd> apart. <kbd>j</kbd>/<kbd>k</kbd> move, <kbd>h</kbd>/<kbd>l</kbd> section, <kbd>Enter</kbd> open, <kbd>c</kbd> compose, <kbd>r</kbd>/<kbd>a</kbd>/<kbd>f</kbd> reply / reply all / forward (in your editor), <kbd>e</kbd> archive, <kbd>d</kbd> trash, <kbd>z</kbd> undo or cancel a send, <kbd>/</kbd> filter, <kbd>s</kbd> Gmail search, <kbd>@</kbd> ask Claude, <kbd>S</kbd> summarise, <kbd>D</kbd> draft a reply, <kbd>T</kbd> today's digest, <kbd>A</kbd> approve an agent's send, <kbd>?</kbd> every key. With no credentials yet it opens a setup screen.
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>P</kbd> — Ports popup ([pattan](https://github.com/Theyashsawarkar/pattan), its own repo; also the `pattan` command): your dev servers' ports with the app, project, status and page title, every listening port, Docker's ports and tunnels (ngrok, cloudflared, tailscale, ssh -R…). <kbd>Enter</kbd> opens `localhost:port` in the browser, <kbd>y</kbd> copies the URL, <kbd>g</kbd> jumps to the tmux pane running it, <kbd>t</kbd> starts a tunnel, <kbd>x</kbd>/<kbd>K</kbd> stop / force stop, <kbd>Tab</kbd> or <kbd>1</kbd>–<kbd>4</kbd> tabs, <kbd>/</kbd> search, <kbd>?</kbd> every key; on a tunnel <kbd>R</kbd> sends one of ngrok's requests again. Also a click on the **󰒋 N** capsule
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>D</kbd> — Docker popup ([nauka](https://github.com/Theyashsawarkar/nauka), its own repo; also the `nauka` command): containers, compose projects, images, volumes, networks and disk use, <kbd>Tab</kbd> apart. <kbd>Enter</kbd> focuses the details (a container's volumes and networks; <kbd>Enter</kbd> on one jumps there, <kbd>Backspace</kbd> back), <kbd>1</kbd>–<kbd>6</kbd> overview/logs/stats/env/inspect/files, <kbd>s</kbd> start/stop, <kbd>r</kbd> restart, <kbd>e</kbd> shell, <kbd>l</kbd> follow logs, <kbd>d</kbd> remove (asks), compose <kbd>u</kbd>/<kbd>d</kbd> up/down, <kbd>P</kbd> prune, <kbd>?</kbd> every key. Also a click on the Docker capsule
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>B</kbd> — Post popup ([vaikhari](https://github.com/Theyashsawarkar/vaikhari), its own repo; also the `vaikhari` command): write once for X and LinkedIn with a live preview of each. <kbd>Ctrl</kbd>+<kbd>S</kbd> posts (LinkedIn goes out, X opens in the browser for your click), <kbd>Ctrl</kbd>+<kbd>T</kbd> schedules, <kbd>Ctrl</kbd>+<kbd>D</kbd> keeps a draft, <kbd>Ctrl</kbd>+<kbd>X</kbd> / <kbd>Ctrl</kbd>+<kbd>L</kbd> toggle the networks, <kbd>Esc</kbd> then <kbd>Tab</kbd> for Queue, Drafts and Posted, <kbd>?</kbd> every key. <kbd>B</kbd> again closes it, keeping what you wrote as a draft
- Click the **"N to review"** capsule on the tmux bar — the same pull requests popup (sangam); a click on a window capsule still selects that window
- Click the **󰇮 N** (unread mail) or **󰭹 N** (unread chats) count on the tmux bar — narada in a popup, on its mail or chat tab (like <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>e</kbd>)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>a</kbd> — jump to the Claude session that has waited longest for you (finished its turn or asks for permission, in another pane); clicking the **"N waiting"** capsule does the same
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>C</kbd> — Claude Code accounts ([vesha](https://github.com/Theyashsawarkar/vesha)); the bar's **"account N%"** capsule shows the active one and its 5-hour usage
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>A</kbd> — Skills and tools for every AI agent ([vishvakarma](https://github.com/Theyashsawarkar/vishvakarma)): every skill, tool and agent; sync, doctor, test a tool, turn one off (`?` lists its keys)
- Click the **󰒋 N** (dev servers) capsule — the ports popup (pattan, like <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>P</kbd>); the Docker capsule opens nauka (like <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>D</kbd>)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>t</kbd> — Scratch shell popup (<kbd>Ctrl</kbd>+<kbd>d</kbd> closes)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>T</kbd> — btop popup
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Tab</kbd> — extrakto: fuzzy-pick paths/URLs/words from the pane
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>S</kbd> — Toggle synchronized input to all panes
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>z</kbd> — Toggle pane zoom
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>h</kbd>/<kbd>j</kbd>/<kbd>k</kbd>/<kbd>l</kbd> — Move focus to the pane left/below/above/right (vim-style)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>n</kbd> / <kbd>p</kbd> — Switch to the next / previous window (wraps around)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Shift</kbd>+<kbd>h</kbd>/<kbd>j</kbd>/<kbd>k</kbd>/<kbd>l</kbd> — Resize pane left/down/up/right (5 columns / 2 rows; repeats without the prefix)
- No arrow keys anywhere in tmux (made for a 60% keyboard): panes are <kbd>h</kbd>/<kbd>j</kbd>/<kbd>k</kbd>/<kbd>l</kbd> after the prefix, the popups (session picker, key search) move with <kbd>Ctrl</kbd>+<kbd>j</kbd>/<kbd>k</kbd>, copy mode with <kbd>h</kbd>/<kbd>j</kbd>/<kbd>k</kbd>/<kbd>l</kbd>, and a floating pane is placed with <kbd>h</kbd>/<kbd>j</kbd>/<kbd>k</kbd>/<kbd>l</kbd> (<kbd>Alt</kbd>+ for half the window)
- <kbd>Alt</kbd>+<kbd>1</kbd>..<kbd>9</kbd> — Select window 1–9 (no prefix needed; a missing window is a silent no-op)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Enter</kbd> — Enter copy mode (the session capsule turns green)
- <kbd>v</kbd> (in copy mode) — Begin visual selection
- <kbd>Esc</kbd> / <kbd>q</kbd> (in copy mode) — Leave copy mode
- <kbd>Ctrl</kbd>+<kbd>v</kbd> (in copy mode) — Toggle rectangle/block selection
- <kbd>y</kbd> (in copy mode) — Copy selection to the Wayland clipboard (`wl-copy`)
- Mouse — drag copies and keeps the highlight (click clears it); double-click copies a word, triple-click a line, in or out of copy mode
