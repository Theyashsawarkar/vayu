-- varna (Vayu's theme engine) -> catppuccin. varna writes the theme's palette
-- to ~/.local/state/varna/nvim.lua; this hands it to catppuccin as
-- color_overrides (latte's slots for a light theme, mocha's for a dark one).
-- `varna apply` calls reload() in every running Neovim (--remote-expr), so
-- the editor recolours without a restart. Without varna: plain catppuccin.
local M = {}

local function state_file()
  local base = vim.env.XDG_STATE_HOME or (vim.env.HOME .. "/.local/state")
  return base .. "/varna/nvim.lua"
end

function M.read()
  local ok, t = pcall(dofile, state_file())
  if ok and type(t) == "table" and type(t.colors) == "table" then
    return t
  end
end

-- catppuccin's opts with the theme's palette merged in.
function M.opts(base)
  local t = M.read()
  local opts = vim.deepcopy(base or M.base or {})
  if t then
    local flavour = t.variant == "light" and "latte" or "mocha"
    opts.flavour = flavour
    opts.background = { light = "latte", dark = "mocha" }
    opts.color_overrides = { [flavour] = t.colors }
  end
  return opts
end

-- lazy.nvim's config for catppuccin: remembers the base opts for reload().
function M.setup(base)
  M.base = base
  require("catppuccin").setup(M.opts(base))
end

function M.reload()
  if not M.base then
    return
  end
  local t = M.read()
  require("catppuccin").setup(M.opts())
  vim.o.background = (t and t.variant == "light") and "light" or "dark"
  vim.cmd.colorscheme("catppuccin")
end

return M
