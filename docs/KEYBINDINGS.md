# Keybindings

Every keybinding here comes straight from `sway/config` and `tmux/.config/tmux/tmux.conf`
-- this list is generated from the real `bindsym`/`bind` lines and their own comments
(the same parsing `scripts/.local/bin/keybind-search.py` does live, bound to
`Super+Shift+/` on the desktop itself), not hand-maintained separately from the
configs that actually define them.

`Super` is the Windows/Cmd key (sway's `$mod`).

## Sway

### Popups & pickers

- <kbd>Super</kbd>+<kbd>m</kbd> — Clipboard history
- <kbd>Super</kbd>+<kbd>.</kbd> — Emoji picker
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>w</kbd> — Wi-Fi picker (scan, connect, toggle)
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>b</kbd> — Bluetooth picker (pair, connect, toggle)
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>d</kbd> — Docker picker (running containers, restart, stop)
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>n</kbd> — Notification history
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>p</kbd> — Power menu (lock / logout / suspend / reboot / shutdown)
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>m</kbd> — rmpc (music player), toggle open/hidden
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>y</kbd> — Search + download music from YouTube
- <kbd>Super</kbd>+<kbd>n</kbd> — Cycle notification mode (normal → silent → dnd)
- <kbd>Super</kbd>+<kbd>Ctrl</kbd>+<kbd>n</kbd> / <kbd>s</kbd> / <kbd>d</kbd> — Jump directly to normal / silent / dnd
- <kbd>Super</kbd>+<kbd>Shift</kbd>+<kbd>/</kbd> — Fuzzy-searchable keybinding reference (this list, live)

### Launch & session

- <kbd>Super</kbd>+<kbd>Return</kbd> — Open a terminal
- <kbd>Super</kbd>+<kbd>d</kbd> — App launcher
- <kbd>Super</kbd>+<kbd>c</kbd> — Calculator
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

### Media & hardware keys

- Volume Mute / Up / Down — Adjust volume (with on-screen indicator)
- Mic Mute — Toggle microphone mute
- Play/Pause, Prev, Next, Stop — Media playback control (`playerctl`)
- Brightness Up / Down — Adjust screen brightness (with on-screen indicator)

### Screenshots & lock

- <kbd>Print</kbd> — Screenshot, full screen
- <kbd>Super</kbd>+<kbd>Print</kbd> — Screenshot, select a region
- <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>;</kbd> — Lock screen

## Tmux

Prefix key is <kbd>Ctrl</kbd>+<kbd>a</kbd> (not tmux's default <kbd>Ctrl</kbd>+<kbd>b</kbd>). Every stock tmux
binding still works too -- this is only the set this repo added or renamed its own note for; the
full list (~260 entries including every stock default) is what `Super+Shift+/`'s Tmux results and
`tmux list-keys` both show.

- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Ctrl</kbd>+<kbd>a</kbd> — Send a literal Ctrl-a to the application
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>|</kbd> — Split horizontally, in the current pane's directory
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>-</kbd> — Split vertically, in the current pane's directory
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>c</kbd> — New window, in the current pane's directory
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>&lt;</kbd>/<kbd>&gt;</kbd> — Swap window left/right
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>r</kbd> — Reload tmux config (mako notification only)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>:</kbd> — Floating command prompt (runs in the real client, never nests)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>s</kbd> — Session picker with live previews (<kbd>Ctrl</kbd>+<kbd>x</kbd> kills, a new name creates)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>w</kbd> — Classic session/window tree
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>L</kbd> — Last session
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>,</kbd> / <kbd>R</kbd> — Rename window (floating input, prefilled)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>$</kbd> — Rename session (floating input, prefilled)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>x</kbd> / <kbd>&amp;</kbd> — Kill pane / window (centred confirm menu)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>K</kbd> — Kill current session, hopping to the next one (confirm menu)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Alt</kbd>+<kbd>k</kbd> — Kill every other session (confirm menu)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Ctrl</kbd>+<kbd>s</kbd> / <kbd>Ctrl</kbd>+<kbd>r</kbd> — Save / restore sessions (tmux-resurrect, mako notification only)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>g</kbd> — lazygit popup in the current directory
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>t</kbd> — Scratch shell popup (<kbd>Ctrl</kbd>+<kbd>d</kbd> closes)
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>T</kbd> — btop popup
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>Tab</kbd> — extrakto: fuzzy-pick paths/URLs/words from the pane
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>S</kbd> — Toggle synchronized input to all panes
- <kbd>Ctrl</kbd>+<kbd>a</kbd> <kbd>z</kbd> — Toggle pane zoom
- <kbd>Alt</kbd>+<kbd>Left</kbd>/<kbd>Right</kbd>/<kbd>Up</kbd>/<kbd>Down</kbd> — Move focus between panes (no prefix needed)
- <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>Left</kbd>/<kbd>Right</kbd> — Resize pane left/right by 5
- <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>Up</kbd>/<kbd>Down</kbd> — Resize pane up/down by 2
- <kbd>Alt</kbd>+<kbd>1</kbd>..<kbd>9</kbd> — Select window 1–9 (no prefix needed; a missing window is a silent no-op)
- <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>1</kbd>..<kbd>6</kbd> — Select window 1–6 (no prefix needed, kitty extended keys)
- <kbd>v</kbd> (in copy mode) — Begin visual selection
- <kbd>Ctrl</kbd>+<kbd>v</kbd> (in copy mode) — Toggle rectangle/block selection
- <kbd>y</kbd> (in copy mode) — Copy selection to the Wayland clipboard (`wl-copy`)
