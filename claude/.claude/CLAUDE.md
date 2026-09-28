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
