#!/usr/bin/env python3
"""The one keybinding registry for the whole desktop (everything but Neovim,
which has its own keymap search).

Every source is re-read live from the real config on each run -- there is no
hand-kept cheat sheet to drift out of sync. Descriptions come from each
tool's own annotation mechanism:

  Sway    ~/.config/sway/config   `#: Description` line directly above a
                                  bindsym (or a run of consecutive ones --
                                  `{}` in the text becomes the last word of
                                  each bound command, e.g. the workspace
                                  number). Modes are detected generically.
  Kitty   ~/.config/kitty/kitty.conf   `#: Description` above each `map`.
  Tmux    live `tmux list-keys -N` per table -- i.e. tmux's own `bind -N
          "note"` from tmux.conf. Custom vs stock is decided by diffing
          against a throwaway `-f /dev/null` server's bindings, so stock
          keys show as such and overridden ones as yours.
  Zed     ~/.config/zed/keymap.json   trailing `// comment` if present,
          otherwise the action name, humanized.
  rmpc    ~/.config/rmpc/config.ron   `keybinds:` sections, action names
          humanized.
  Scripts `# keybind: <Source>/<scope> | <keys> | <description>` lines in
          the popup/picker scripts, for keys that only exist inside them
          (fzf --bind etc.), e.g. the tmux session picker's Ctrl+x.
          Same annotation in /etc/sysctl.d (source Kernel): the Magic
          SysRq combos; and in /usr/local/lib/vayu-elevate (source Vayu):
          the root approval window.

Front-ends:
  (no args)          wofi popup, Super+Shift+/ in sway. Enter copies the line.
  --tmux-fzf         fzf list of tmux keys for the tmux `prefix ?` popup;
                     prints the picked entry's table<TAB>key for tmux_keys.sh
                     to replay with `send-keys -K`.
  --list [SOURCE]    plain table of everything (or one source) on stdout.
  --check [--tmux-conf FILE]
                     exit 1 listing every binding without a real
                     description, or bound twice in the same scope. Run it
                     after any keybinding change (see ~/dotfiles/CLAUDE.md).
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
SWAY_CONFIG = HOME / ".config/sway/config"
KITTY_CONFIG = HOME / ".config/kitty/kitty.conf"
ZED_KEYMAP = HOME / ".config/zed/keymap.json"
RMPC_CONFIG = HOME / ".config/rmpc/config.ron"
ANNOTATED_SCRIPT_DIRS = [
    HOME / ".tmux/scripts",
    HOME / ".local/bin",
    HOME / ".config/sway/scripts",
    # Kernel Magic SysRq combos (system/etc/sysctl.d/99-sysrq.conf).
    Path("/etc/sysctl.d"),
    # vayu-elevate's approval window (ai/elevate/dialog.py, root-owned).
    Path("/usr/local/lib/vayu-elevate"),
]

# Same Catppuccin Mocha hues the wifi/bluetooth pickers use, one per source.
SOURCE_COLORS = {
    "Sway": "#89DCEB",   # Sky
    "Tmux": "#94E2D5",   # Teal
    "Kitty": "#F5C2E7",  # Pink
    "Zed": "#89B4FA",    # Blue
    "rmpc": "#CBA6F7",   # Mauve
    "Kernel": "#F38BA8", # Red
}
SCOPE_COLOR = "#FAB387"   # Peach
DIM_COLOR = "#7F849C"     # Overlay1: stock tmux defaults


# Every description reads "<Verb> <object> (details)": "Kill window",
# "Open lazygit popup (current directory)". wofi's fuzzy match is an
# ordered subsequence match, so searching action-then-object ("kill
# window") only works if every description is written in that order.
# --check enforces it for hand-written descriptions: the first word must
# be one of these verbs (add a verb here if a new one is genuinely needed).
SEARCH_HINT = "action + object, e.g. kill window, open lazygit, raise volume"
TMUX_SEARCH_HINT = "action + object, e.g. kill window, split pane, rename session"
VERBS = set("""
add alternate begin cancel clear close confirm continue copy create cut cycle delete
describe detach edit enter evaluate exit focus force format go grow hover install invert
jump kill leave lock lower move normal open paste pick play quit raise rate record
reload remove rename reopen rerun rescan reset resize restore rotate run save scroll
search seek select send set show shrink shuffle split start step stop swap switch
take toggle trash update
""".split())


def verb_first(desc):
    return desc.split()[0].split("/")[0].lower() in VERBS if desc.split() else False


def entry(source, keys, desc, scope=None, origin="custom", documented=True, **extra):
    """One binding. `documented` False = no real description (only the raw
    command) -- what --check reports."""
    return dict(source=source, keys=keys, desc=desc, scope=scope,
                origin=origin, documented=documented, **extra)


def last_word(command):
    return command.split()[-1] if command.split() else command


# --------------------------------------------------------------------- Sway
def parse_sway():
    try:
        lines = SWAY_CONFIG.read_text().splitlines()
    except OSError:
        return []

    variables, entries = {}, []
    mode, note = None, None
    mode_keys = {}  # mode name -> key that enters it

    for raw in lines:
        line = raw.strip()

        if line.startswith("#:"):
            note = line[2:].strip() or None
            continue
        if line.startswith("#"):
            continue  # ordinary comments neither set nor clear a #: note
        if not line:
            note = None
            continue

        m = re.match(r"set\s+(\$\S+)\s+(.+)", line)
        if m:
            variables[m.group(1)] = m.group(2)
            note = None
            continue

        m = re.match(r'mode\s+"([^"]+)"\s*\{', line)
        if m:
            mode, note = m.group(1), None
            continue
        if line == "}":
            mode, note = None, None
            continue

        m = re.match(r"bind(?:sym|code)\s+((?:--\S+\s+)*)(\S+)\s+(.+)", line)
        if not m:
            note = None
            continue
        _flags, keys, command = m.groups()
        for var, val in sorted(variables.items(), key=lambda kv: -len(kv[0])):
            keys = keys.replace(var, val)
        keys = keys.replace("Mod4", "Super").replace("Mod1", "Alt")
        command = command.strip()

        mm = re.match(r'mode\s+"([^"]+)"', command)
        if mm and mode is None:
            mode_keys[mm.group(1)] = keys

        if note:
            desc, documented = note.replace("{}", last_word(command)), True
        else:
            desc, documented = command, False
        entries.append(entry("Sway", keys, desc, scope=mode, documented=documented,
                             command=command))

    for e in entries:
        if e["scope"]:
            enter = mode_keys.get(e["scope"])
            e["scope"] = f"{e['scope']} mode" + (f", {enter} first" if enter else "")
    return entries


# -------------------------------------------------------------------- Kitty
def parse_kitty():
    try:
        lines = KITTY_CONFIG.read_text().splitlines()
    except OSError:
        return []
    kitty_mod = "ctrl+shift"
    entries, note = [], None
    for raw in lines:
        line = raw.strip()
        if line.startswith("#:"):
            note = line[2:].strip() or None
            continue
        if line.startswith("#"):
            continue
        if not line:
            note = None
            continue
        m = re.match(r"kitty_mod\s+(\S+)", line)
        if m:
            kitty_mod = m.group(1)
        m = re.match(r"map\s+(\S+)\s+(.+)", line)
        if not m:
            note = None
            continue
        keys, action = m.groups()
        keys = keys.replace("kitty_mod", kitty_mod)
        keys = ">".join("+".join(p.capitalize() if len(p) > 1 else p for p in chord.split("+"))
                        for chord in keys.split(">"))
        entries.append(entry("Kitty", keys, note or action, documented=bool(note),
                             command=action))
    return entries


# --------------------------------------------------------------------- Tmux
TMUX_KEY_NAMES = {
    "PPage": "PageUp", "NPage": "PageDown", "DC": "Delete", "IC": "Insert",
    "BSpace": "Backspace", "BTab": "Shift+Tab",
}

# Plugins bind without -N; name them here rather than re-binding their keys.
TMUX_PLUGIN_NOTES = [
    (r"extrakto/scripts/open\.sh", "Pick paths/URLs/words from the pane (extrakto)"),
    (r"tpm/bindings/install_plugins", "Install plugins listed in tmux.conf (TPM)"),
    (r"tpm/bindings/update_plugins", "Update plugins (TPM)"),
    (r"tpm/bindings/clean_plugins", "Remove plugins no longer listed (TPM)"),
]


def tmux_key(key):
    mods = []
    while re.match(r"^[CMS]-.", key):
        mods.append({"C": "Ctrl", "M": "Alt", "S": "Shift"}[key[0]])
        key = key[2:]
    return "+".join(mods + [TMUX_KEY_NAMES.get(key, key)])


def humanize_tmux_command(cmd):
    m = re.search(r"send-keys\s+-\w*X\w*\s+([\w-]+)", cmd)
    if m:
        return m.group(1).replace("-", " ").capitalize()
    return cmd if len(cmd) <= 80 else cmd[:77] + "..."


def _tmux(*args, socket=None, conf=None):
    cmd = ["tmux"]
    if socket:
        cmd += ["-S", socket]  # absolute path inside a private temp dir
    if conf:
        cmd += ["-f", conf]
    try:
        r = subprocess.run(cmd + list(args), capture_output=True, text=True, timeout=5)
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""
    return r.stdout


def _tmux_table(table, socket=None, conf=None):
    """{key: (text, has_note, raw_command)} for one key table."""
    start = ["start-server", ";"] if conf else []
    both = _tmux(*start, "list-keys", "-N", "-a", "-P", "", "-T", table, socket=socket, conf=conf)
    noted = _tmux(*start, "list-keys", "-N", "-P", "", "-T", table, socket=socket, conf=conf)
    raw = _tmux(*start, "list-keys", "-T", table, socket=socket, conf=conf)
    noted_keys = {ln.split(None, 1)[0] for ln in noted.splitlines() if ln.strip()}
    commands = {}
    for ln in raw.splitlines():
        m = re.match(r"bind-key\s+(?:-r\s+)?-T\s+\S+\s+(\S+)\s+(.*)", ln)
        if m:
            k = m.group(1)
            commands[k[1:] if k.startswith("\\") and len(k) > 1 else k] = m.group(2).strip()
    out = {}
    for ln in both.splitlines():
        parts = ln.strip().split(None, 1)
        if len(parts) == 2:
            k, text = parts
            out[k] = (text, k in noted_keys, commands.get(k, text))
    return out


# --check --tmux-conf FILE: describe FILE as loaded into a throwaway server
# instead of the live one, so an edit is checked before anyone reloads it.
TMUX_CONF = None


def parse_tmux():
    # Throwaway servers (the stock-bindings probe, and the --tmux-conf
    # check) live on sockets in a private temp dir, removed afterwards, so
    # nothing is left in /tmp/tmux-UID and nothing can collide.
    tmp = tempfile.mkdtemp(prefix="keybind-search-")
    probe = os.path.join(tmp, "probe")
    sock = os.path.join(tmp, "check") if TMUX_CONF else None
    try:
        if sock:
            _tmux("-f", TMUX_CONF, "start-server", socket=sock)
        return _parse_tmux(sock, probe)
    finally:
        for s in (sock, probe):
            if s:
                _tmux("kill-server", socket=s)
        shutil.rmtree(tmp, ignore_errors=True)


def _parse_tmux(sock, probe):
    if not sock and not _tmux("list-sessions").strip():
        return []  # no server running: nothing live to describe
    prefix = _tmux("show-options", "-gv", "prefix", socket=sock).strip() or "C-a"
    copy_table = "copy-mode-vi" if _tmux("show-options", "-gv", "mode-keys", socket=sock).strip() == "vi" else "copy-mode"
    tables = [("prefix", None), ("root", None), (copy_table, "tmux copy mode")]

    entries = []
    for table, scope in tables:
        live = _tmux_table(table, socket=sock)
        stock = _tmux_table(table, socket=probe, conf="/dev/null")
        for key, (text, has_note, command) in live.items():
            if re.search(r"Mouse|Wheel|Click|Drag", key):
                continue
            stock_cmd = stock.get(key, (None, None, None))[2]
            origin = "default" if stock_cmd == command else "custom"
            documented = True
            if has_note:
                desc = text
            else:
                desc = next((n for pat, n in TMUX_PLUGIN_NOTES if re.search(pat, command)), None)
                if desc:
                    origin = "plugin"
                else:
                    desc = humanize_tmux_command(command)
                    # A stock key, or a copy-mode `send-keys -X <action>`,
                    # names itself; a custom bind without -N does not.
                    documented = origin == "default" or command.startswith("send-keys")
            keys = f"{tmux_key(prefix)} {tmux_key(key)}" if table == "prefix" else tmux_key(key)
            entries.append(entry("Tmux", keys, desc, scope=scope, origin=origin,
                                 documented=documented, table=table, tmux_key=key,
                                 command=command))
    rank = {"custom": 0, "plugin": 1, "default": 2}
    entries.sort(key=lambda e: rank[e["origin"]])  # stable: keeps table order
    return entries


# ---------------------------------------------------------------------- Zed
def humanize_action(action, comment=None):
    """project_panel::ToggleHideHidden -> "Toggle hide hidden (project panel)":
    Zed action names are VerbObject, so this is already action-then-object."""
    ns, _, name = action.rpartition("::")
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).lower().capitalize()
    # Zed's vocabulary -> the words people actually search with
    for zed_word, verb in (("New ", "Create new "), ("Deploy", "Open"), ("Activate", "Focus")):
        if words.startswith(zed_word):
            words = verb + words[len(zed_word):]
    details = [d for d in (ns.replace("_", " "), comment) if d]
    return words + (f" ({'; '.join(details)})" if details else "")


def zed_key(keys):
    def chord(c):
        parts = c.split("-") if c not in ("-",) else [c]
        return "+".join(p.capitalize() if len(p) > 1 else p for p in parts)
    return " ".join(chord(c) for c in keys.split())


def parse_zed():
    try:
        lines = ZED_KEYMAP.read_text().splitlines()
    except OSError:
        return []
    entries, context = [], None
    for raw in lines:
        m = re.match(r'\s*"context"\s*:\s*"([^"]*)"', raw)
        if m:
            context = " ".join(m.group(1).split())
            continue
        m = re.match(r'\s*"([^"]+)"\s*:\s*(?:\[\s*)?"([^"]+)"[^/]*(?://\s*(.*))?$', raw)
        if not m or m.group(1) in ("context", "bindings"):
            continue
        keys, action, comment = m.groups()
        desc = humanize_action(action, comment.strip().strip('"') if comment and comment.strip() else None)
        scope = context if context and len(context) <= 40 else (context[:39] + "…" if context else None)
        entries.append(entry("Zed", zed_key(keys), desc, scope=scope, command=action))
    return entries


# --------------------------------------------------------------------- rmpc
RMPC_SPECIAL = {"<CR>": "Enter", "<Esc>": "Escape", "<Space>": "Space", "<Tab>": "Tab",
                "<S-Tab>": "Shift+Tab", "<PageUp>": "PageUp", "<PageDown>": "PageDown"}


def rmpc_key(keys):
    out = []
    for tok in re.findall(r"<[^>]+>|.", keys):
        if tok in RMPC_SPECIAL:
            out.append(RMPC_SPECIAL[tok])
        elif tok.startswith("<"):
            mods, _, k = tok[1:-1].rpartition("-")
            names = [{"C": "Ctrl", "S": "Shift", "A": "Alt", "M": "Alt"}.get(x, x) for x in mods.split("-") if x]
            if len(k) == 1 and k.isupper():
                names.append("Shift")
                k = k.lower()
            out.append("+".join(names + [k]))
        else:
            out.append(tok)
    return " ".join(out)


RMPC_NAMES = {
    "VolumeUp": "Raise volume", "VolumeDown": "Lower volume",
    "NextTrack": "Play next track", "PreviousTrack": "Play previous track",
    "NextTab": "Go to next tab", "PreviousTab": "Go to previous tab",
    "NextResult": "Go to next search result", "PreviousResult": "Go to previous search result",
    "Up": "Move cursor up", "Down": "Move cursor down", "Left": "Move cursor left", "Right": "Move cursor right",
    "PaneUp": "Focus pane above", "PaneDown": "Focus pane below",
    "PaneLeft": "Focus pane left", "PaneRight": "Focus pane right",
    "UpHalf": "Scroll half a page up", "DownHalf": "Scroll half a page down",
    "PageUp": "Scroll a page up", "PageDown": "Scroll a page down",
    "Top": "Jump to top", "Bottom": "Jump to bottom",
    "MoveUp": "Move item up", "MoveDown": "Move item down",
    "CommandMode": "Enter command mode", "EnterSearch": "Enter search",
    "Partition": "Show partitions", "ContextMenu": "Open context menu",
    "Update": "Update database", "Rescan": "Rescan library",
    "AddRandom": "Add random songs", "Add": "Add to queue", "AddAll": "Add all to queue",
    "Select": "Select item", "InvertSelection": "Invert selection",
    "FocusInput": "Focus input", "Rate": "Rate song", "Rename": "Rename item",
    "Delete": "Delete item", "DeleteAll": "Delete all", "Shuffle": "Shuffle queue",
    "Stop": "Stop playback", "Play": "Play song", "Confirm": "Confirm selection",
    "Close": "Close popup", "Quit": "Quit rmpc", "JumpToCurrent": "Jump to current song",
}


def rmpc_action(action):
    name, _, args = action.partition("(")
    if name in RMPC_NAMES and "Save" not in name:
        return RMPC_NAMES[name]
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).lower().capitalize()
    q = re.search(r'"([^"]+)"', args)
    if q:
        return f"{words}: {q.group(1)}"
    if name == "Save":
        return "Save " + ("all" if "all: true" in args else "selection") + " to playlist"
    return words


def parse_rmpc():
    try:
        lines = RMPC_CONFIG.read_text().splitlines()
    except OSError:
        return []
    entries, inside, section = [], False, None
    for raw in lines:
        if re.match(r"\s*keybinds\s*:\s*\(", raw):
            inside = True
            continue
        if not inside:
            continue
        m = re.match(r"\s*(\w+)\s*:\s*\{", raw)
        if m:
            section = m.group(1)
            continue
        if re.match(r"\s*\),?\s*$", raw) and section is None:
            break
        if re.match(r"\s*\},?\s*$", raw):
            section = None
            continue
        m = re.match(r'\s*"([^"]+)"\s*:\s*(.+?),\s*$', raw)
        if m and section:
            keys, action = m.groups()
            scope = None if section == "global" else section
            entries.append(entry("rmpc", rmpc_key(keys), rmpc_action(action), scope=scope,
                                 command=action))
    return entries


# ------------------------------------------------------------------ Scripts
def parse_script_annotations():
    entries, seen = [], set()
    for d in ANNOTATED_SCRIPT_DIRS:
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            real = os.path.realpath(f)
            if real in seen or not f.is_file():
                continue
            seen.add(real)
            try:
                text = f.read_text(errors="ignore")
            except OSError:
                continue
            # Source must be a plain word, so the <Source>/<scope> usage
            # examples in docstrings (this file's own) never parse.
            for m in re.finditer(r"#\s*keybind:\s*(\w[^|<\n]*?)\s*\|\s*([^|\n]+?)\s*\|\s*(.+)", text):
                where, keys, desc = (g.strip() for g in m.groups())
                source, _, scope = where.partition("/")
                entries.append(entry(source.strip(), keys, desc, scope=scope.strip() or None,
                                     origin="script", file=f.name))
    return entries


def all_entries():
    return (parse_sway() + parse_tmux() + parse_script_annotations()
            + parse_kitty() + parse_zed() + parse_rmpc())


# ---------------------------------------------------------------- Front-ends
MAX_DESC_LEN = 78


def short(desc):
    return desc if len(desc) <= MAX_DESC_LEN else desc[: MAX_DESC_LEN - 1].rstrip() + "…"


def wofi_line(e):
    color = SOURCE_COLORS.get(e["source"], "#CDD6F4")
    esc = html.escape
    keys = f"{e['keys']:22s}"
    if e["origin"] == "default":
        keys = f'<span foreground="{DIM_COLOR}">{esc(keys)}</span>'
    else:
        keys = esc(keys)
    line = f'<span foreground="{color}">{esc(e["source"]):5s}</span> {keys} {esc(short(e["desc"]))}'
    tags = [t for t in (e["scope"], "default" if e["origin"] == "default" else None) if t]
    if tags:
        line += f'<span foreground="{SCOPE_COLOR}">  [{esc(", ".join(tags))}]</span>'
    return line


def run_wofi():
    entries = all_entries()
    if not entries:
        subprocess.run([
            "notify-send", "-u", "critical",
            "-i", "/usr/share/icons/AdwaitaLegacy/48x48/legacy/dialog-error.png", "Keybindings",
            "Couldn't parse any keybindings -- check the configs are readable",
        ])
        sys.exit(1)
    # --height 680 is what --lines 12 drew; --lines sizes the list from the
    # rows wofi has at its first draw, so it sometimes came up one row tall
    # (reproduced 2026-09-29).
    result = subprocess.run(
        ["wofi", "--dmenu", "--insensitive", "--matching", "fuzzy",
         "--prompt", SEARCH_HINT, "--height", "680"],
        input="\n".join(wofi_line(e) for e in entries), capture_output=True, text=True,
    )
    selection = html.unescape(re.sub(r"<[^>]+>", "", result.stdout.strip()))
    selection = re.sub(r"\s{2,}", "  ", selection)
    if not selection:
        return
    # Popen, not run: wl-copy stays alive to serve the selection.
    proc = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE, text=True)
    proc.stdin.write(selection)
    proc.stdin.close()
    subprocess.run([
        "notify-send", "-u", "low",
        "-i", "/usr/share/icons/candy-icons/apps/scalable/org.kde.plasma.clipboard.svg",
        "Keybinding (copied)", selection,
    ])


def ansi(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"\033[38;2;{r};{g};{b}m"


def run_tmux_fzf():
    """Lines for the prefix ? popup: tmux keys plus tmux-scoped script keys.
    Hidden fields 1-2 (table, raw key) tell tmux_keys.sh what to replay."""
    reset = "\033[0m"
    rows = []
    for e in parse_tmux() + [e for e in parse_script_annotations() if e["source"] == "Tmux"]:
        keycol = ansi(DIM_COLOR if e["origin"] == "default" else "#D095A4") + f"{e['keys']:20s}" + reset
        tags = [t for t in (e["scope"], "default" if e["origin"] == "default" else None) if t]
        tag = f"  {ansi(SCOPE_COLOR)}[{', '.join(tags)}]{reset}" if tags else ""
        rows.append(f"{e.get('table', '-')}\t{e.get('tmux_key', '-')}\t{keycol} {e['desc']}{tag}")
    if not rows:
        return
    r = subprocess.run(
        ["fzf", "--ansi", "--delimiter", "\t", "--with-nth", "3",
         "--layout", "reverse", "--info", "inline-right", "--no-separator", "--no-scrollbar",
         "--prompt", "❯ ", "--ghost", TMUX_SEARCH_HINT,
         "--pointer", "▌", "--marker", " ", "--gutter", " ",
         "--border", "rounded", "--border-label", " 󰌌 tmux keys ", "--border-label-pos", "3",
         "--padding", "1,2",
         "--header", "⏎ run it · esc close · everything else: Super+Shift+/\n",
         "--color", "bg:-1,bg+:#2A2D35,fg:#D7DDE6,fg+:#FFFFFF,hl:#D095A4,hl+:#D095A4",
         "--color", "border:#D095A4,label:#D095A4,prompt:#D095A4,pointer:#D095A4,header:#6C7086,info:#6C7086,query:#D7DDE6"],
        input="\n".join(rows), capture_output=True, text=True,
    )
    pick = r.stdout.strip()
    if pick:
        print("\t".join(pick.split("\t")[:2]))


def run_list(source=None):
    for e in all_entries():
        if source and e["source"].lower() != source.lower():
            continue
        tags = ", ".join(t for t in (e["scope"], e["origin"] if e["origin"] != "custom" else None) if t)
        print(f"{e['source']:6s} {e['keys']:26s} {e['desc']}" + (f"  [{tags}]" if tags else ""))


def run_check():
    entries = all_entries()
    problems = []
    if not any(e["source"] == "Tmux" for e in entries):
        problems.append("tmux: no running server, tmux bindings were NOT checked (start tmux and re-run)")
    for e in entries:
        if not e["documented"]:
            where = {"Sway": f"add a '#: <description>' line above it in {SWAY_CONFIG}",
                     "Kitty": f"add a '#: <description>' line above it in {KITTY_CONFIG}",
                     "Tmux": "give it -N \"<description>\" in tmux.conf (or a TMUX_PLUGIN_NOTES entry here for a plugin key)",
                     }.get(e["source"], "describe it")
            problems.append(f"{e['source']}: {e['keys']} ({e.get('command', e['desc'])}) has no description -- {where}")
    for e in entries:
        if e["documented"] and e["origin"] in ("custom", "script") and e["source"] in ("Sway", "Kitty", "Tmux") \
                and not verb_first(e["desc"]):
            problems.append(f"{e['source']}: {e['keys']} -- '{e['desc']}' must start with a verb "
                            f"(\"<Verb> <object> (details)\", e.g. 'Open emoji picker'); known verbs: VERBS in keybind-search.py")
    seen = {}
    for e in entries:
        if e["origin"] == "default":
            continue
        k = (e["source"], e["scope"], e["keys"])
        if k in seen and e["source"] in ("Sway", "Kitty"):
            problems.append(f"{e['source']}: {e['keys']} is bound twice"
                            + (f" in {e['scope']}" if e["scope"] else "")
                            + f" ('{seen[k]}' and '{e['desc']}')")
        seen.setdefault(k, e["desc"])
    counts = {}
    for e in entries:
        counts[e["source"]] = counts.get(e["source"], 0) + 1
    summary = ", ".join(f"{s} {n}" for s, n in counts.items())
    if problems:
        print("keybind-search --check: FAIL\n  " + "\n  ".join(problems))
        print(f"({summary})")
        sys.exit(1)
    print(f"keybind-search --check: OK ({summary})")


def main():
    args = sys.argv[1:]
    if not args:
        run_wofi()
    elif args[0] == "--tmux-fzf":
        run_tmux_fzf()
    elif args[0] == "--list":
        run_list(args[1] if len(args) > 1 else None)
    elif args[0] == "--check":
        global TMUX_CONF
        if len(args) > 2 and args[1] == "--tmux-conf":
            TMUX_CONF = os.path.expanduser(args[2])
        run_check()
    elif args[0] == "--json":
        json.dump(all_entries(), sys.stdout, indent=1)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
