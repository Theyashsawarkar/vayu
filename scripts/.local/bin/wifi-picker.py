#!/usr/bin/env python3
"""Themed wrapper around the system's networkmanager_dmenu (see
ARCHITECTURE.md's networkmanager-dmenu entry). Adds category-based Pango
colors -- network / saved connection / command -- on top of upstream's
existing active-connection highlight, so the different kinds of rows in
the menu ("connect to this network" vs "a saved connection" vs "a command
like Rescan/Enable/Disable") are visually distinguishable at a glance
instead of all rendering the same color. Also strips the Bluetooth toggle
out of the command list -- this menu is WiFi-only now, Bluetooth gets its
own separate picker (bluetooth-picker.py) with its own unique options.

Monkeypatches three functions (get_wofi_highlight_markup, get_selection,
create_other_actions) on the real installed module rather than forking
the whole script -- everything else (NetworkManager interaction,
connecting, scanning, password prompts) still comes from the real,
maintained upstream package. Category detection is by Action.func
identity (process_ap == a real network) plus the ":SAVED" suffix upstream
already puts on saved-connection action names -- both are core to how
the tool actually works, not incidental detail likely to silently
change, but wrapped defensively (_category() swallows any
AttributeError) so a future upstream refactor degrades to "no color"
rather than a crash.

get_selection is simplified from upstream to the wofi-only code path
(upstream branches on rofi/wofi/plain-dmenu; this repo only ever uses
wofi, dmenu_command=wofi is hardcoded in config.ini) -- kept otherwise as
close to a literal copy as possible, since the line-generation and
selection-matching have to stay in exact sync or clicking an entry either
does nothing or fires the wrong action.
"""
import importlib.machinery
import importlib.util
import json
import os
import re
import subprocess
import sys

NMDM_PATH = "/usr/bin/networkmanager_dmenu"

# spec_from_file_location can't infer a loader for a file with no .py
# extension (it returns None rather than raising, which then fails
# confusingly one line later) -- has to be given an explicit loader.
_loader = importlib.machinery.SourceFileLoader("networkmanager_dmenu", NMDM_PATH)
spec = importlib.util.spec_from_loader(_loader.name, _loader)
nmdm = importlib.util.module_from_spec(spec)
_loader.exec_module(nmdm)

# Catppuccin Mocha, matching the rest of the bar's palette.
CATEGORY_COLORS = {
    "network": "#89DCEB",  # Sky -- matches waybar's own network.wifi color
    "saved": "#94E2D5",    # Teal -- calm, "known and ready, not live-scanned"
    "command": "#FAB387",  # Peach -- "this changes something" energy
}

# "┃ " prefix on the active line, inside the same colored span so it
# inherits the highlight foreground -- Pango <span> markup has no border
# attribute at all (checked: foreground/background/underline/strikethrough/
# weight/style/size exist, border does not), so a real CSS-style border
# around the connected entry isn't achievable here. This is the closest
# honest approximation: a colored sidebar tick, same idea as an "active
# indicator bar" in a lot of TUI/statusline designs, on top of the
# existing filled-background highlight rather than instead of it.
ACTIVE_MARKER = "┃ "  # heavy vertical line

_COMMAND_FUNC_NAMES = (
    "toggle_wifi",
    "toggle_networking",
    "toggle_wwan",
    "launch_connection_editor",
    "delete_connection",
    "rescan_wifi",
    "show_wifi_password",
    "prompt_saved",  # the "Saved connections" row that opens the submenu
)
_COMMAND_FUNCS = {
    getattr(nmdm, name) for name in _COMMAND_FUNC_NAMES if hasattr(nmdm, name)
}


def _category(action):
    try:
        if str(action).endswith(":SAVED"):
            return "saved"
        if action.func in _COMMAND_FUNCS:
            return "command"
        if action.func is getattr(nmdm, "process_ap", None):
            return "network"
    except AttributeError:
        pass
    return None


def themed_markup(action):
    """Replacement for nmdm.get_wofi_highlight_markup -- colors every line
    by category. The active connection still gets the original
    highlight_fg/bg/bold treatment from config.ini on top, checked first
    so it always wins over the category color, plus the ACTIVE_MARKER
    prefix as a border stand-in."""
    style = ""
    prefix = ""
    if action.is_active:
        highlight_fg = nmdm.CONF.get("dmenu", "highlight_fg", fallback="")
        highlight_bg = nmdm.CONF.get("dmenu", "highlight_bg", fallback="")
        highlight_bold = nmdm.CONF.getboolean(
            "dmenu", "highlight_bold", fallback=True
        )
        if highlight_fg:
            style += f'foreground="{highlight_fg}" '
        if highlight_bg:
            style += f'background="{highlight_bg}" '
        if highlight_bold:
            style += 'weight="bold" '
        prefix = ACTIVE_MARKER
    else:
        color = CATEGORY_COLORS.get(_category(action))
        if color:
            style += f'foreground="{color}" '

    if not style:
        return str(action)
    return f"<span {style}>" + prefix + str(action) + "</span>"


def themed_get_selection(all_actions):
    inp = [themed_markup(action) for action in all_actions]
    active_lines = [
        index for index, action in enumerate(all_actions) if action.is_active
    ]

    prompt = nmdm.CONF.get("dmenu", "prompt", fallback="Networks")
    command = nmdm.dmenu_cmd(f"{prompt} ", active_lines=active_lines)
    sel = nmdm.run_dmenu(command, "\n".join(inp)).stdout

    if not sel.rstrip():
        sys.exit()

    action = [
        i
        for i in all_actions
        if str(i).strip() == sel.strip() or themed_markup(i) == sel.strip()
    ]
    if len(action) != 1:
        raise ValueError(f"Selection was ambiguous: '{str(sel.strip())}'")
    return action[0]


_orig_create_other_actions = nmdm.create_other_actions


def wifi_only_other_actions(client):
    """WiFi-only menu -- strips the Bluetooth toggle upstream mixes in.
    Bluetooth gets its own separate picker with its own unique options.
    Adds the hotspot (vayu-hotspot) rows."""
    return [
        a for a in _orig_create_other_actions(client) if a.func is not nmdm.toggle_bluetooth
    ] + hotspot_actions()


# Full path: wofi runs from sway, without the login shell's PATH.
HOTSPOT = os.path.expanduser("~/.local/bin/vayu-hotspot")


def _hotspot(*args):
    """Runs vayu-hotspot and shows its first line (or its error) as a
    notification; the waybar capsule updates on its own."""
    r = subprocess.run([HOTSPOT, *args], capture_output=True, text=True)
    out = (r.stdout or r.stderr).strip().splitlines()
    msg = re.sub(r"\x1b\[[0-9;]*m", "", out[0] if out else "")
    subprocess.run(["notify-send", "-a", "Hotspot", "-i", "network-wireless-hotspot",
                    "Hotspot" if r.returncode == 0 else "Hotspot failed", msg])


def _copy_hotspot_password(password):
    subprocess.run(["wl-copy"], input=password, text=True)
    subprocess.run(["notify-send", "-a", "Hotspot", "-i", "network-wireless-hotspot",
                    "Hotspot", "Password copied"])


def hotspot_actions():
    """Start/stop rows for the hotspot, only when vayu-hotspot exists and
    this laptop's Wi-Fi card can be an access point (it says so if not)."""
    try:
        r = subprocess.run([HOTSPOT, "status", "--json"], capture_output=True, text=True, timeout=5)
        st = json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        st = None
    if not st:
        return []
    if st["on"]:
        n = st["client_count"]
        return [nmdm.Action(f"Stop hotspot \"{st['ssid']}\" ({n} connected)", _hotspot, ["off"], active=True),
                nmdm.Action(f"Copy hotspot password ({st['password']})", _copy_hotspot_password, [st["password"]])]
    return [nmdm.Action("Start hotspot (share this laptop's internet)", _hotspot, ["on"])]


# The hotspot rows are commands too (same color as Rescan/Disable).
_COMMAND_FUNCS |= {_hotspot, _copy_hotspot_password}

nmdm.get_wofi_highlight_markup = themed_markup
nmdm.get_selection = themed_get_selection
nmdm.create_other_actions = wifi_only_other_actions

if __name__ == "__main__":
    nmdm.main()
