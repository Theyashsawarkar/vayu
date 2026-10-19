# dotfiles (vayu) -- notes for AI agents

For any agent working in this repo (Codex, Aider, Claude Code...).
`CLAUDE.md` has the full notes and applies to every agent, not only
Claude: read it before changing anything. The rules that matter most are
repeated here; when a rule changes, change it in both files.

- Stow-managed: `~/dotfiles/<pkg>/...` is symlinked into `~`. Edit files
  here, never a copy in `~`.
- Day-to-day work on `development`; every change gets a dated
  `CHANGELOG.md` entry (`docs/VERSIONING.md`).
- Commands that need root go through `vayu-elevate` (docs/AI-TOOLS.md),
  never pasted sudo commands.
- Any keybinding created, changed or removed must show up in the central
  keybinding search: describe it verb-first and annotate it as CLAUDE.md
  "Keybindings" says, then make `~/.local/bin/keybind-search.py --check`
  pass.

## Plugins: every plugin in its own repository

Every plugin we create for any tool (tmux, Neovim, zsh, waybar, rmpc...)
lives in its **own repository** under github.com/Theyashsawarkar, and vayu
**pulls it in** through that tool's plugin mechanism. Plugin source is never
copied into this repo. That way each plugin is independent: it is tested,
versioned and upgraded on its own, and people can install just the plugins
they want without the rest of vayu.

- **Where:** develop it in `~/personal/<name>` (the personal git identity
  applies there; see the global notes) and push it to
  `github.com/Theyashsawarkar/<name>`, public. Name it after the tool's
  convention: `tmux-<name>`, `<name>.nvim`, `zsh-<name>`...
- **How vayu includes it:** the tool's own plugin manager, so `install.sh`
  and updates handle it: tmux `set -g @plugin 'Theyashsawarkar/<name>'` in
  tmux.conf (TPM; `install.sh` clones every `@plugin` line, and
  `plugins-missing.sh` clones new ones on the next tmux load), Neovim a
  lazy.nvim spec, and so on. A tool with no plugin manager gets a
  `clone_if_missing` in `install.sh`.
- **Standalone first:** the plugin must work on a stock setup without vayu:
  sane defaults, no hardcoded vayu paths or `/home/yash`, a README with
  install steps for that tool alone and every option. Vayu's look and
  behaviour go through the plugin's options, set in vayu's config (e.g.
  tmux-gh-pr's `@gh-pr-launcher` points at vayu's `popup.sh`).
- **Keybindings still show up in the search:** keys a plugin binds use
  `bind -N "<Verb> <object> (details)"` (or a `TMUX_PLUGIN_NOTES` entry),
  and keys inside its scripts keep their `# keybind:` lines: tmux plugins'
  `scripts/` dirs (`~/.tmux/plugins/*/scripts`) are scanned. Run
  `keybind-search.py --check` after installing it, as for any key change.
- **Changes:** fix or extend a plugin in its repo, with its own CHANGELOG
  and tags; vayu's CHANGELOG notes only what changes for vayu (a plugin
  added or removed, options changed). To test a local plugin change inside
  vayu, temporarily symlink `~/.tmux/plugins/<name>` to `~/personal/<name>`
  and put the real clone back after pushing (`prefix U` updates).
- **Existing:** `tmux-gh-pr` (prefix G, pull requests popup).
