-- Pause Neovim's polling timers while it doesn't have focus.
--
-- An idle Neovim woke the CPU ~117 times a second (~4 ms of CPU a second),
-- all from plugins polling on timers whether you're in it or not: lualine
-- drains its refresh queue every 16 ms and redraws the clock every 1 s,
-- noice checks for UI updates every 33 ms and its own health every 1 s,
-- snacks' statuscolumn clears its cache every 50 ms, which-key checks the
-- mode every 50 ms and lazy.nvim stats its config every 2 s. In a tmux
-- session nobody is attached to, or a pane you're not in, none of it shows.
--
-- So 2 s after FocusLost (tmux's focus-events, on in tmux.conf; the 2 s lets
-- a debounce you just triggered finish) we stop every timer due within
-- 2 s: repeating ones and the one-shot ones plugins re-arm in a loop. On
-- FocusGained, or the first key you press, whichever comes first (so a
-- missed focus event can't leave the editor stale), the same timers start
-- again with their own callbacks. While paused, a pane you can see but
-- aren't in keeps its last statusline and signs until you go back to it.
local M = {}

local WINDOW_MS = 2000 -- pause timers due within this; also the grace period
local paused = {} -- { handle, repeat_ms, due_ms }
local focused = true

function M.pause()
  if focused or #paused > 0 then
    return
  end
  vim.uv.walk(function(h)
    if h:get_type() == "timer" and not h:is_closing() and h:is_active() then
      local rep, due = h:get_repeat(), h:get_due_in()
      if (rep > 0 and rep <= WINDOW_MS) or (rep == 0 and due <= WINDOW_MS) then
        h:stop()
        paused[#paused + 1] = { h, rep, due }
      end
    end
  end)
end

function M.resume()
  focused = true
  if #paused == 0 then
    return
  end
  local timers = paused
  paused = {}
  for _, t in ipairs(timers) do
    local h, rep, due = t[1], t[2], t[3]
    if not h:is_closing() and not h:is_active() then
      if rep > 0 then
        pcall(h.again, h)
      else
        -- A one-shot: fire it once, after what was left of its wait.
        pcall(function()
          h:set_repeat(math.max(1, due))
          h:again()
          h:set_repeat(0)
        end)
      end
    end
  end
  pcall(function()
    require("lualine").refresh()
  end)
end

function M.paused()
  return #paused
end

function M.setup()
  local group = vim.api.nvim_create_augroup("quiet_focus", { clear = true })
  vim.api.nvim_create_autocmd("FocusLost", {
    group = group,
    callback = function()
      focused = false
      vim.defer_fn(M.pause, WINDOW_MS)
    end,
  })
  vim.api.nvim_create_autocmd("FocusGained", { group = group, callback = M.resume })
  vim.on_key(function()
    if not focused or #paused > 0 then
      vim.schedule(M.resume)
    end
  end, vim.api.nvim_create_namespace("quiet_focus"))
end

return M
