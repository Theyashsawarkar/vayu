-- Switched from onedark.nvim to match the rest of this desktop -- every
-- other themed app (waybar, mako, wofi, kitty, tmux, rmpc, sway borders,
-- swaylock, the GTK theme itself) is already Catppuccin Mocha with a
-- Mauve accent; Neovim was the one thing left on an unrelated palette.
--
-- catppuccin was already sitting in lazy-lock.json as an installed
-- dependency (of something else, never actually activated) before this
-- -- no new plugin download needed, just properly wiring it up.
--
-- Also a real, measured performance fix, not just aesthetics:
-- onedark.lua called `require("onedark").setup()` then
-- `require("onedark").load()` directly in its own `config` function,
-- instead of the standard LazyVim `opts.colorscheme` pattern below.
-- `nvim --startuptime` showed that ad-hoc loading path costing ~6ms on
-- its own (sourcing onedark's colors file alone was the single most
-- expensive individual line in the whole startup log after lazy.nvim's
-- own bootstrap) -- LazyVim's own colorscheme mechanism is the
-- community-optimized path every other LazyVim plugin/extra also
-- expects, not just a style preference.
return {
  {
    "catppuccin/nvim",
    name = "catppuccin",
    -- lazy=false explicitly, not just implied by defaults.lazy=false in
    -- lazy.lua -- real bug #1, root-caused: LazyVim's own core spec
    -- (lazyvim/plugins/colorscheme.lua) declares catppuccin with
    -- `lazy = true`, which won over this file's implied default, so
    -- this spec's own config/opts never actually ran (confirmed
    -- directly: a debug write at the top of a temporary `config`
    -- function never fired).
    --
    -- priority = 10001, not the original 1000 -- real bug #2, found
    -- right after fixing #1 alone didn't change anything: LazyVim's OWN
    -- plugin entry (lazyvim/plugins/init.lua) is
    -- `{ "LazyVim/LazyVim", priority = 10000, lazy = false, ... }`.
    -- lazy.nvim loads eager plugins in descending priority order, and
    -- LazyVim's own `config` is what actually runs `vim.cmd.colorscheme(...)`
    -- (from `opts.colorscheme` below) -- at priority 1000, that command
    -- ran a full 9000-priority-levels before catppuccin's own `setup()`
    -- ever got called, so it sourced `colors/catppuccin.lua` and hit
    -- the exact same `M.setup()` empty-args fallback as the lazy=true
    -- bug did, on catppuccin's bare defaults again. One priority level
    -- above LazyVim's own 10000 guarantees this plugin's real `setup(opts)`
    -- runs first every time, regardless of how LazyVim's own core specs
    -- are ever reordered in a future update.
    lazy = false,
    priority = 10001,
    opts = {
      flavour = "mocha",
      -- Matches kitty/tmux/rmpc's own real compositor-level
      -- transparency elsewhere on this desktop, not just nvim's own
      -- background left unset -- same "glass" language throughout.
      transparent_background = true,
      -- Explicit integrations for exactly what's actually installed
      -- (checked lazy-lock.json first, not enabled speculatively) --
      -- an unlisted integration just means that plugin keeps its own
      -- default highlighting instead of Catppuccin's, not an error, but
      -- leaving these on means blink.cmp's menu, noice's UI, and
      -- which-key's popup all actually match now instead of looking
      -- like a different theme bled through.
      integrations = {
        blink_cmp = true,
        noice = true,
        notify = true,
        which_key = true,
        treesitter = true,
        mini = { enabled = true },
        native_lsp = { enabled = true },
      },
    },
  },
  { "LazyVim/LazyVim", opts = { colorscheme = "catppuccin" } },
}
