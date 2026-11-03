# Global notes

- System config lives in `~/dotfiles` (stow-managed, see its `CLAUDE.md`).
  Read `~/dotfiles/CLAUDE.md` before changing anything there.
- **Keybindings:** whenever you create, change, or delete a keybinding
  anywhere on this system (sway, tmux, kitty, zed, nāda, or keys inside a
  script/popup) -- everything except Neovim -- it must show up correctly
  in the central keybinding search (`Super+Shift+/`, and `prefix ?` for
  tmux). Describe it verb-first, `<Verb> <object> (details)` like "Kill
  current window" (users search action + object). Annotate it as
  `~/dotfiles/CLAUDE.md` describes, then run
  `~/.local/bin/keybind-search.py --check` and make it pass.
- **Commands you can't run yourself** (need root, or blocked by your
  sandbox or a permission rule): don't ask the user to copy-paste them.
  Send them to `dvarapala` (JSON on stdin: `requester`, `reason`,
  `commands: [{cmd, why, as, cwd}]`; `dvarapala --help` / `--schema`).
  `"as": "root"` (default) runs as root via `bash -c` from `/` and needs
  the user's password; `"as": "user"` runs as the user in `cwd` (absolute,
  default home), outside your sandbox, approved with a click. The user sees
  each command with its `why`, marked ROOT or YOU, and ticks what to allow;
  you get JSON back with each command's `state`
  (ok/failed/skipped/declined/not_run), exit code and output. No stdin:
  use non-interactive flags (`pacman --noconfirm`). User commands get a
  filtered session environment, not yours: pass what they need on the
  command line. Respect declined commands; never retry a denied request
  unasked, and never use it to get around a refusal. If `dvarapala` is
  missing, fall back to giving the commands as before.
- **Every tool we make has a logo and a Sanskrit shloka**: a Sanskrit name,
  `assets/logo.svg` in the family's style, and one real, verified verse as
  its tag, in its README, on its website and on its own screen where there's
  room. Never write or adapt a verse. The `tool-identity` skill has the
  details (vishvakarma gives it to every agent).
- **Our tools' screens**: colour that means something (the theme's colours:
  red danger, green done, yellow waiting, peach what to look for, accent where
  you are), and forms that open read-only, so stray typing changes nothing.
  The `tool-identity` skill has the details.
