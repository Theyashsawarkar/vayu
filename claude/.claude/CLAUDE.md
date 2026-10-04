# Global notes

- System config lives in `~/dotfiles` (stow-managed, see its `CLAUDE.md`).
  Read `~/dotfiles/CLAUDE.md` before changing anything there.
- **Keybindings:** whenever you create, change, or delete a keybinding
  anywhere on this system (sway, tmux, kitty, zed, rmpc, or keys inside a
  script/popup) -- everything except Neovim -- it must show up correctly
  in the central keybinding search (`Super+Shift+/`, and `prefix ?` for
  tmux). Describe it verb-first, `<Verb> <object> (details)` like "Kill
  current window" (users search action + object). Annotate it as
  `~/dotfiles/CLAUDE.md` describes, then run
  `~/.local/bin/keybind-search.py --check` and make it pass.
- **Commands that need root:** don't ask the user to copy-paste sudo
  commands. Send them to `vayu-elevate` (JSON on stdin: `requester`,
  `reason`, `commands: [{cmd, why}]`; `vayu-elevate --help` / `--schema`).
  The user sees each command with its `why` in an approval window, ticks
  what to allow and types their password once; you get JSON back with each
  command's `state` (ok/failed/skipped/declined/not_run), exit code and
  output. Commands run as root via `bash -c`, from `/`, with no stdin: use
  non-interactive flags (`pacman --noconfirm`). Respect declined commands;
  never retry a denied request unasked. If `vayu-elevate` is missing,
  fall back to giving the commands as before.
