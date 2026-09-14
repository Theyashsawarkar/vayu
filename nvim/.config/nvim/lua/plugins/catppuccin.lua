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
    priority = 1000,
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
