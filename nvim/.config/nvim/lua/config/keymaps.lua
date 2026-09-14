-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

-- Quick escape: "jk" typed within timeoutlen (default 300ms/LazyVim's
-- own setting, see options.lua's default) in insert mode acts as <Esc>.
-- Plain two-character insert-mode mapping -- if you type "j" and pause
-- past timeoutlen, or type some other letter next, it's just "j"
-- followed by whatever you actually typed, not the escape; only a fast
-- "jk" fires it.
vim.keymap.set("i", "jk", "<Esc>", { desc = "Exit insert mode" })
