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

## Hardware: detect it, never assume it

Vayu runs on more than the laptop it was built on (different CPUs, GPUs,
Wi-Fi cards, batteries, screens). Anything hardware-related is detected at
runtime or install time, with a clear message when the hardware can't do
it: device names (`wlan0`, `BAT0`, `eDP-1`) are looked up, not written in;
capabilities are checked before use (e.g. vayu-hotspot asks NetworkManager
whether the Wi-Fi card can be an access point and has 5 GHz); packages
that depend on the CPU or GPU come from `packages/hardware.sh`. A feature
the hardware can't support says so and how to get around it, instead of
failing silently. Known limits go in `docs/TROUBLESHOOTING.md`
("Hardware: a different laptop...").

## Plugins: every plugin in its own repository

Every plugin we create for any tool (tmux, Neovim, zsh, waybar, Vyom...)
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
  sangam's `@sangam-launcher` points at vayu's `popup.sh`).
- **A tool first, when it can be one:** if what we build is useful
  outside its host (sangam is a PR tool, not only a tmux popup), make it a
  command anyone can install and run on its own (an installer, `make
  install`, a package, `--help`, a `doctor` check), with the host
  integration as one way to use it. The plugin manager's copy can then be
  linked onto PATH by `install.sh`.
- **Keybindings still show up in the search:** keys a plugin binds use
  `bind -N "<Verb> <object> (details)"` (or a `TMUX_PLUGIN_NOTES` entry),
  and keys inside its scripts keep their `# keybind:` lines: tmux plugins'
  `scripts/` and `bin/` dirs (`~/.tmux/plugins/*/{scripts,bin}`) are
  scanned. Run
  `keybind-search.py --check` after installing it, as for any key change.
- **Changes:** fix or extend a plugin in its repo, with its own CHANGELOG
  and tags; vayu's CHANGELOG notes only what changes for vayu (a plugin
  added or removed, options changed). To test a local plugin change inside
  vayu, temporarily symlink `~/.tmux/plugins/<name>` to `~/personal/<name>`
  and put the real clone back after pushing (`prefix U` updates).
- **Existing:** [`sangam`](https://github.com/Theyashsawarkar/sangam)
  (pull requests: a command, and the prefix G popup; `install.sh` links
  TPM's copy to `~/.local/bin/sangam`).
  [`vyom`](https://github.com/Theyashsawarkar/vyom), the launcher/panels
  runtime that replaced wofi and nwg-bar, and its tools, each its own
  repo: dvara (apps), ganit (calculator), smriti (clipboard), bhava (emoji),
  tarang (Wi-Fi + hotspot), setu (Bluetooth), doot (phone), patra (Docker),
  suchana (notifications), raga (YouTube), mudra (keybindings), urja
  (battery), vishram (power menu), kendra (quick settings). `install.sh`
  clones Vyom to `~/.local/share/vyom/core` and the tools
  (`VYOM_TOOLS`, packages/manifest.sh) to `.../plugins/`; Vayu's settings
  for them are the `vyom/` stow package. A script that needs a picker uses
  `vyom dmenu -p PROMPT` (stdin choices, stdout pick), never a new wofi.
