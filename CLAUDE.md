# dotfiles (vayu) -- notes for Claude

Stow-managed: `~/dotfiles/<pkg>/...` is symlinked into `~`. Edit files here
(the symlink targets), never a copy in `~`. Branch/release process:
`docs/VERSIONING.md` (day-to-day work on `development`; every change gets a
dated `CHANGELOG.md` entry). A change with a trade-off, failure mode or
known glitch also gets a symptom-first section in `docs/TROUBLESHOOTING.md`
(on the site as Troubleshooting); see VERSIONING.md.

Commands that need root: use `vayu-elevate` (ai/, docs/AI-TOOLS.md) rather
than asking the user to paste sudo commands.

## Keybindings: one registry, always in sync

`scripts/.local/bin/keybind-search.py` is THE place to find any keybinding
on this system except Neovim (which has its own keymap search). It reads
every source live and backs two searches:

- **Super+Shift+/** (sway) -- every source, in wofi.
- **prefix ?** (tmux) -- tmux keys in an fzf popup; Enter runs the binding.

So whenever you **create, change, or delete a keybinding anywhere**, in the
same change:

1. Write the description as **`<Verb> <object> (details)`**: "Kill current
   window", "Open lazygit popup (current directory)", "Raise volume 5%",
   never "Lazygit popup" or "Volume up". Both searches match in typed
   order, and their placeholder tells the user to search action + object
   ("kill window"), so a noun-first description is unfindable that way.
   `--check` rejects a first word that isn't in `VERBS` in the script. Add a
   verb there only if no existing one fits. Put the specifics in the
   parentheses and keep the object word people would type (window, pane,
   session, volume, screenshot...).

2. Describe it with that source's annotation (the search only shows what is
   annotated, and `--check` fails otherwise):

   | Source | Where | How to describe it |
   |---|---|---|
   | Sway | `sway/.config/sway/config` | `#: Description` line directly above the `bindsym` (applies to the consecutive run of bindsyms below it; `{}` = last word of each command, e.g. `#: Switch to workspace {}`) |
   | Tmux | `tmux/.config/tmux/tmux.conf` | `bind -N "Description" ...` (plugin keys without -N: add to `TMUX_PLUGIN_NOTES` in the script) |
   | Kitty | `kitty/.config/kitty/kitty.conf` | `#: Description` line directly above the `map` |
   | Zed | `zed/.config/zed/keymap.json` | trailing `// Description` (else the action name is shown) |
   | rmpc | `rmpc/.config/rmpc/config.ron` | nothing -- action names are shown humanized |
   | Keys inside a script/popup (fzf `--bind`, pickers) | the script, in `~/.tmux/scripts`, `~/.local/bin` or `~/.config/sway/scripts` | `# keybind: <Source>/<scope> \| <keys> \| <description>`, e.g. `# keybind: Tmux/session picker \| Ctrl+x \| Kill the highlighted session` |
| Kernel Magic SysRq | `system/etc/sysctl.d/99-sysrq.conf` (scanned at `/etc/sysctl.d`, so run `system/apply.sh` first) | `# keybind: Kernel \| <keys> \| <description>` |
| vayu-elevate approval window | `ai/elevate/dialog.py` (scanned at `/usr/local/lib/vayu-elevate`, so run `ai/apply.sh` first) | `# keybind: Vayu/root approval \| <keys> \| <description>` in its docstring |

   A new tool with its own keybinding config gets a parser in
   `keybind-search.py` (and a row here) rather than going unlisted.

3. Reload what you changed (`tmux source-file ~/.config/tmux/tmux.conf`,
   `swaymsg reload`), then run:

   ```
   ~/.local/bin/keybind-search.py --check          # must print OK
   ~/.local/bin/keybind-search.py --list <source>  # eyeball the entry
   ```

   `--check` also catches a key bound twice in the same sway/kitty scope.
   It needs a running tmux server to check tmux (it says so if not).

4. Update `docs/KEYBINDINGS.md` if it lists that area.

A Claude Code hook (PostToolUse on Edit/Write, `keybind-check-hook.sh`)
runs `--check` automatically after edits to these files and reports any
failure back -- fix it, don't ignore it. It is registered in
`~/.claude/settings.json` by `scripts/.local/bin/claude-hooks-install.sh`
(run by `install.sh`; merges with jq, since Claude Code rewrites that file
itself). The global `~/.claude/CLAUDE.md` is the stowed `claude/` package.
Edits made through Bash/sed don't trigger the hook: run `--check` yourself.

## tmux specifics worth knowing

- Popups (`display-popup`) must never run a command that attaches a tmux
  client: a client started inside a popup attaches *to the popup*. Collect
  input in the popup, act after it closes (see `cmd_prompt.sh`,
  `tmux_keys.sh`), and pin tmux calls to the invoking client with `-c`.
- tmux.conf is re-sourced on every `prefix r` and on attach: never use
  `set -a`/`-as` on options (they grow on every reload); use fixed array
  slots like `terminal-features[90]`.
- No status-line messages: notify via `notify-send -a tmux` (mako) instead.
- Test on an isolated server, never the live one:
  `tmux -L outer -f /dev/null new -d -s o -x 160 -y 45 "env -u TMUX tmux -L inner -f ~/.config/tmux/tmux.conf new -A -s main"`
  and drive it with `tmux -L outer send-keys -t o ...`. Point resurrect at
  a scratch dir first (`tmux -L inner set -g @resurrect-dir ...`).
