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
  Scripts `# keybind: <Source>/<scope>[:<mode>] | <keys> | <description>` lines in
          the popup/picker scripts, for keys that only exist inside them
          (fzf --bind etc.), e.g. the tmux session picker's Ctrl+x.
          Same annotation in /etc/sysctl.d (source Kernel): the Magic
          SysRq combos; in /usr/local/lib/dvarapala (source Dvarapala): the
          root approval window; in /usr/local/lib/pramana (source
          Pramana): the polkit password prompt.
          The optional `:normal` / `:insert` / `:visual` / `:command`
          suffix on the scope is the vim mode the key works in (the Space
          grammar, docs/KEYBINDINGS.md); it becomes the entry's `mode`.
          `# keybind-group: <Source>/<scope> | Space y | Copy` names a
          leader group; every key under it gets the group path.

Front-ends:
  (no args)          opens mudra (a Vyom tool, Super+Shift+/), which reads --json.
  --json             every binding as JSON (mudra's source).
  --tmux-fzf         fzf list of tmux keys for the tmux `prefix ?` popup;
                     prints the picked entry's table<TAB>key for tmux_keys.sh
                     to replay with `send-keys -K`.
  --tmux-fzf TABLE   the same, only tables starting with TABLE (the
                     launcher's palette: `--tmux-fzf launch`).
  --list [SOURCE] [--keys "space y"]
                     plain table of everything (or one source) on stdout;
                     --keys keeps bindings whose keys start with that
                     sequence, in order ("space y" = the Copy group).
  --groups           the leader groups (# keybind-group lines).
  --check [--strict] [--tmux-conf FILE]
                     exit 1 listing every binding without a real
                     description, or bound twice in the same scope. Run it
                     after any keybinding change (see ~/dotfiles/CLAUDE.md).
                     Space-grammar rules (a reserved leader group used for
                     something else, `g` bound beside `g g` in one mode, an
                     annotated capital the code never checks, a lone key
                     that does something irreversible) are WARNINGS, and
                     failures with --strict.
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
    # Vayu's own tmux plugins (own repos, cloned by TPM), e.g. sangam's
    # keys in its bin/sangam. Third-party plugins don't use the annotation.
    # (not kosha's `<name>.kosha-release` copy, kept while a plugin is
    # `kosha link`ed: an old clone, e.g. narada's sandesh-era keys)
    *sorted(p for p in (HOME / ".tmux/plugins").glob("*/scripts") if "." not in p.parent.name),
    *sorted(p for p in (HOME / ".tmux/plugins").glob("*/bin") if "." not in p.parent.name),
    # Vyom (the launcher/panels runtime) and its tools, each a separate
    # repo: their keys are annotated in their Python packages.
    HOME / ".local/share/vyom/core/vyom",
    # (not kosha's `<name>.kosha-release` copy, kept while a tool is
    # `kosha link`ed: its old keys would show up beside the new ones)
    *sorted(p for p in (HOME / ".local/share/vyom/plugins").glob("*/*")
            if (p / "__init__.py").exists() and "." not in p.parent.name),
    # nāda, the music player (its own repo): keys annotated in its package.
    HOME / ".local/share/nada/nada",
    # vesha, the Claude Code account switcher (its own repo): its switcher keys.
    HOME / ".local/share/vesha/vesha",
    # vishvakarma, skills and tools for every AI agent (its own repo): its app's keys.
    HOME / ".local/share/vishvakarma/vishvakarma",
    # vinyasa, the settings app (its own repo): its window's keys.
    HOME / ".local/share/vinyasa/vinyasa",
    # drishya, the video player (its own repo): its window's keys.
    HOME / ".local/share/drishya/drishya",
    # ekatva, phone and laptop as one (its own repo): its desktop window's
    # keys, found through the `ekatva` command's link into the repo.
    *([Path(os.path.realpath(HOME / ".local/bin/ekatva")).parents[2] / "desktop/src/renderer/src"]
      if (HOME / ".local/bin/ekatva").exists() else []),
    # Kernel Magic SysRq combos (system/etc/sysctl.d/99-sysrq.conf).
    Path("/etc/sysctl.d"),
    # dvarapala's approval window (own repo; installed root-owned).
    Path("/usr/local/lib/dvarapala"),
    # pramana, the polkit password prompt (own repo; installed root-owned).
    Path("/usr/local/lib/pramana"),
]

# Colours come from the theme (varna's palette.json, written on every
# `varna apply`); without varna, Vayu's own. One palette name per source.
def _palette():
    import json
    defaults = {"sky": "#89DCEB", "teal": "#94E2D5", "pink": "#F5C2E7", "blue": "#89B4FA", "mauve": "#CBA6F7",
                "red": "#F38BA8", "yellow": "#F9E2AF", "lavender": "#B4BEFE", "green": "#A6E3A1", "peach": "#FAB387", "overlay1": "#7F849C",
                "overlay0": "#6C7086", "accent2": "#F5C2E7", "fg": "#D7DDE6", "text": "#CDD6F4", "surface0": "#313244", "subtext0": "#A6ADC8"}
    path = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"), "varna", "palette.json")
    try:
        with open(path) as f:
            data = json.load(f)
        theme = (data.get("tools") or {}).get("tmux") or data   # tmux's own theme, if it has one
        return {**defaults, **{k: v for k, v in theme["colors"].items() if isinstance(v, str)}}
    except (OSError, ValueError, KeyError, TypeError):
        return defaults


PALETTE = _palette()
SOURCE_COLORS = {src: PALETTE[name] for src, name in {
    "Sway": "sky", "Tmux": "teal", "Kitty": "pink", "Zed": "blue", "rmpc": "mauve", "Kernel": "red", "Vyom": "lavender",
    "Nada": "pink", "Drishya": "sky", "Dvarapala": "green", "Pramana": "yellow", "Vesha": "peach", "Vinyasa": "teal"}.items()}
SCOPE_COLOR = PALETTE["peach"]
DIM_COLOR = PALETTE["overlay1"]   # stock tmux defaults
KEY_COLOR = PALETTE["accent2"]


# Every description reads "<Verb> <object> (details)": "Kill window",
# "Open lazygit popup (current directory)". wofi's fuzzy match is an
# ordered subsequence match, so searching action-then-object ("kill
# window") only works if every description is written in that order.
# --check enforces it for hand-written descriptions: the first word must
# be one of these verbs (add a verb here if a new one is genuinely needed).
SEARCH_HINT = "action + object, e.g. kill window, open lazygit, raise volume"
TMUX_SEARCH_HINT = "action + object, e.g. kill window, split pane, rename session"
VERBS = set("""
add alternate approve begin build cancel clear close confirm connect continue copy create
cut cycle decline delete describe detach disconnect edit enter evaluate exit focus follow
force format go grow hover install invert jump kill leave lock lower merge move normal open
paste pause pick play post pull quit raise rate record reload remove rename reopen request
rerun rescan reset resize restart restore rotate run save schedule scroll search seek select
send set show shrink shuffle sort split start step stop swap switch take toggle trash undo update
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
STRICT = False   # --check --strict: Space-grammar warnings fail too


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
    # Every other key table too: the floating-pane `move` table, and the
    # launcher's `launch*` tables (prefix Space, drawn by whichkey.sh).
    skip = {"prefix", "root", "copy-mode", "copy-mode-vi"}
    others = sorted({m.group(1) for m in re.finditer(r"-T\s+(\S+)", _tmux("list-keys", socket=sock))} - skip)
    paths = _launch_paths(sock, prefix)
    for t in others:
        tables.append((t, "launcher" if t in paths else f"tmux {t} table"))

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
            extra = {}
            if table == "prefix":
                keys = f"{tmux_key(prefix)} {tmux_key(key)}"
            elif table in paths:
                keys = f"{paths[table]} {tmux_key(key)}"
                extra["leader"] = True
            else:
                keys = tmux_key(key)
            entries.append(entry("Tmux", keys, desc, scope=scope, origin=origin,
                                 documented=documented, table=table, tmux_key=key,
                                 command=command, **extra))
    rank = {"custom": 0, "plugin": 1, "default": 2}
    entries.sort(key=lambda e: rank[e["origin"]])  # stable: keeps table order
    return entries


def _launch_paths(sock, prefix):
    """{table: "Ctrl+a Space n"}: how each launcher table is reached. A
    binding that opens one runs `whichkey.sh '<client>' <table>`; follow
    those from the prefix table down."""
    raw = _tmux("list-keys", socket=sock)
    opens = {}
    for ln in raw.splitlines():
        m = re.match(r"bind-key\s+(?:-r\s+)?-T\s+(\S+)\s+(\S+)\s+(.*)", ln)
        if not m:
            continue
        t = re.search(r"whichkey\.sh\s+\S+\s+'?(launch[\w-]*)", m.group(3))
        if t:
            k = m.group(2)
            opens[t.group(1)] = (m.group(1), k[1:] if k.startswith("\\") and len(k) > 1 else k)
    paths = {}

    def path(table, depth=0):
        if table in paths:
            return paths[table]
        if table not in opens or depth > 8:
            return None
        parent, key = opens[table]
        base = tmux_key(prefix) if parent == "prefix" else path(parent, depth + 1)
        if base is None and parent != "root":
            return None
        paths[table] = f"{base} {tmux_key(key)}".strip() if base else tmux_key(key)
        return paths[table]

    for t in opens:
        path(t)
    return paths


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
MODES = ("normal", "insert", "visual", "command")
GROUPS = []   # `# keybind-group:` lines, filled by parse_script_annotations


def split_mode(scope):
    """"ganit calculator:normal" -> ("ganit calculator", "normal")."""
    base, sep, mode = scope.rpartition(":")
    if sep and mode.strip().lower() in MODES:
        return base.strip(), mode.strip().lower()
    return scope, None


# Single keys spelled in full; anything else lowercase of 2-3 letters
# ("gg", "dd", "cw") is a sequence of single keys.
KEY_WORDS = {"esc", "tab", "end", "del", "ins", "spc"}


def key_seqs(keys):
    """Every alternative of an annotation's keys as a token tuple:
    "gg / G" -> [("g","g"), ("G",)], "Space y y" -> [("Space","y","y")].
    Ranges and prose ("1..9", "new name + Enter") stay single tokens."""
    out = []
    for alt in re.split(r"\s+/\s+|\s+\|\s+|\s+or\s+", keys.strip()):
        # prose, a range, or a count placeholder ("N G", ": N"; a lone N
        # is the key): one opaque token
        if re.search(r"[()–,]|\.\.|\bthen\b|\s\+\s|\s-\s|\sN\b|\bN\s", alt.strip()):
            out.append((alt.strip(),))
            continue
        toks = []
        for t in alt.split():
            if re.fullmatch(r"[a-z]{2,3}", t) and t not in KEY_WORDS:
                toks.extend(t)
            else:
                toks.append(t)
        if toks:
            out.append(tuple(toks))
    return out


def key_query_match(query, keys):
    """Ordered prefix match of a key query ("space y", "<leader>y", "gg")
    against an entry's keys: True when one alternative starts with it."""
    q = re.sub(r"<leader>|\bspc\b|␣", " space ", query, flags=re.I)
    want = []
    for t in q.split():
        if t.lower() == "space":
            want.append("space")
        elif re.fullmatch(r"[a-z]{2,3}", t) and t not in KEY_WORDS:
            want.extend(t)
        else:
            want.append(t)
    if not want:
        return False
    for seq in key_seqs(keys):
        norm = [t.lower() if t.lower() == "space" or "+" in t else t for t in seq]
        if len(norm) >= len(want) and all(
                a == b or (len(b) > 1 and a.lower() == b.lower()) for a, b in zip(norm, want, strict=False)):
            return True
    return False


def parse_script_annotations():
    entries, seen = [], set()
    GROUPS.clear()
    for d in ANNOTATED_SCRIPT_DIRS:
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            real = os.path.realpath(f)
            if real in seen or not f.is_file():
                continue
            seen.add(real)
            try:
                with open(f, "rb") as fh:
                    if b"\0" in fh.read(4096):
                        continue   # a compiled program (a plugin's bin/): no annotations, and slow to read
                text = f.read_text(errors="ignore")
            except OSError:
                continue
            # Source must be a plain word, so the <Source>/<scope> usage
            # examples in docstrings (this file's own) never parse.
            # (a line of its own: not a tool's generator writing one in an f-string)
            for m in re.finditer(r"^[ \t]*#\s*keybind-group:\s*(\w[^|<\n]*?)\s*\|\s*([^|\n]+?)\s*\|\s*(.+)", text, re.M):
                where, keys, name = (g.strip() for g in m.groups())
                source, _, scope = where.partition("/")
                scope, mode = split_mode(scope.strip())
                GROUPS.append(dict(source=source.strip(), scope=scope or None, mode=mode,
                                   keys=keys, name=name, file=f.name))
            for m in re.finditer(r"#\s*keybind:\s*(\w[^|<\n]*?)\s*\|\s*([^|\n]+?)\s*\|\s*(.+)", text):
                where, keys, desc = (g.strip() for g in m.groups())
                source, _, scope = where.partition("/")
                scope, mode = split_mode(scope.strip())
                extra = {"path": str(f)}
                if mode:
                    extra["mode"] = mode
                if key_seqs(keys) and any(q[0] == "Space" for q in key_seqs(keys)):
                    extra["leader"] = True
                if source.strip() == "Vyom":
                    # Which Vyom tool it belongs to (its package's directory,
                    # or "vyom" for every panel), so mudra can group Vyom's
                    # keys per tool and find them by the tool's name.
                    extra["tool"] = d.parent.name if d.parent.name != "core" else "vyom"
                entries.append(entry(source.strip(), keys, desc, scope=scope.strip() or None,
                                     origin="script", file=f.name, **extra))
    # Each leader key gets its which-key path of group names
    # ("Space y y" under a ganit group line naming "Space y" Copy).
    for e in entries:
        if not e.get("leader"):
            continue
        names = []
        for g in GROUPS:
            if g["source"] != e["source"] or (g["scope"] and not (e["scope"] or "").startswith(g["scope"])):
                continue
            gseq = key_seqs(g["keys"])
            if gseq and any(len(q) > len(gseq[0]) and q[:len(gseq[0])] == gseq[0] for q in key_seqs(e["keys"])):
                names.append((len(gseq[0]), g["name"]))
        if names:
            e["group"] = [n for _, n in sorted(set(names))]
    return entries


def all_entries():
    return (parse_sway() + parse_tmux() + parse_script_annotations()
            + parse_kitty() + parse_zed() + parse_rmpc())


# ---------------------------------------------------------------- Front-ends
MAX_DESC_LEN = 78


def short(desc):
    return desc if len(desc) <= MAX_DESC_LEN else desc[: MAX_DESC_LEN - 1].rstrip() + "…"


def run_panel():
    """The desktop front-end is mudra, a Vyom tool (Super+Shift+/), which
    reads `--json` from this script."""
    os.execvp(os.path.expanduser("~/.local/bin/vyom"), ["vyom", "mudra"])


def ansi(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"\033[38;2;{r};{g};{b}m"


def run_groups():
    parse_script_annotations()
    for g in GROUPS:
        where = g["source"] + (f"/{g['scope']}" if g["scope"] else "") + (f":{g['mode']}" if g["mode"] else "")
        print(f"{where:34s} {g['keys']:14s} {g['name']}")


def run_tmux_fzf(only=None):
    """Lines for the prefix ? popup: tmux keys plus tmux-scoped script keys.
    Hidden fields 1-2 (table, raw key) tell tmux_keys.sh what to replay."""
    reset = "\033[0m"
    P = PALETTE
    rows = []
    if only:   # the launcher's palette: just its own tables (tmux's, no script keys)
        picked = [e for e in parse_tmux() if e.get("table", "").startswith(only)]
    else:
        picked = parse_tmux() + [e for e in parse_script_annotations() if e["source"] == "Tmux"]
    for e in picked:
        keycol = ansi(DIM_COLOR if e["origin"] == "default" else KEY_COLOR) + f"{e['keys']:20s}" + reset
        tags = [t for t in (e["scope"], "default" if e["origin"] == "default" else None) if t]
        tag = f"  {ansi(SCOPE_COLOR)}[{', '.join(tags)}]{reset}" if tags else ""
        rows.append(f"{e.get('table', '-')}\t{e.get('tmux_key', '-')}\t{keycol} {e['desc']}{tag}")
    if not rows:
        return
    # Normal/Insert modes, the same as every tmux picker (fzf-vim.sh):
    # typing searches; Esc goes to NORMAL (j/k, gg/G, q), Esc again closes.
    vim = []
    helper = HOME / ".tmux/scripts/fzf-vim.sh"
    if helper.exists():
        try:
            vim = subprocess.run(["bash", str(helper), "--print0", " keys " if not only else " launcher "],
                                 capture_output=True, text=True, timeout=5).stdout.split("\0")[:-1]
        except subprocess.SubprocessError:
            vim = []
    r = subprocess.run(
        ["fzf", *vim, "--input-border", "rounded", "--ansi", "--delimiter", "\t", "--with-nth", "3",
         "--layout", "reverse", "--info", "inline-right", "--no-separator", "--no-scrollbar",
         "--prompt", "❯ ", "--ghost", TMUX_SEARCH_HINT,
         "--pointer", "▌", "--marker", " ", "--gutter", " ",
         # The tmux popup draws the border and the " keys" title.
         "--padding", "1,2",
         "--header", "⏎ run it · ctrl-j/k move · esc normal mode (j/k, q), again closes · everything else: Super+Shift+/\n",
         "--color", f"bg:-1,bg+:{P['surface0']},fg:{P['fg']},fg+:{P['text']},"
                    f"hl:{P['accent2']},hl+:{P['accent2']}",
         "--color", f"border:{P['accent2']},label:{P['accent2']},prompt:{P['accent2']},pointer:{P['accent2']},"
                    f"header:{P['subtext0']},info:{P['overlay1']},query:{P['fg']}"],
        input="\n".join(rows), capture_output=True, text=True,
        env={**os.environ, "SHELL": "bash"},   # fzf-vim.sh's transforms are bash
    )
    pick = r.stdout.strip()
    if pick:
        print("\t".join(pick.split("\t")[:2]))


def run_list(source=None, keys=None):
    for e in all_entries():
        if source and e["source"].lower() != source.lower():
            continue
        if keys and not key_query_match(keys, e["keys"]):
            continue
        tags = ", ".join(t for t in (e["scope"], e.get("mode"), e["origin"] if e["origin"] != "custom" else None) if t)
        print(f"{e['source']:6s} {e['keys']:26s} {e['desc']}" + (f"  [{tags}]" if tags else ""))


# The Space grammar (docs/KEYBINDINGS.md): letters after Space that mean
# the same thing in every tool, and the first words their keys may start
# with. A tool may leave a group empty, never use it for something else.
RESERVED = {
    "Space": ("palette", None),
    "?": ("keys", {"show", "open", "search"}),
    "q": ("close", {"close", "quit", "leave", "exit", "hide"}),
    "t": ("tabs", {"switch", "go", "show", "open", "jump", "focus", "move"}),
    "u": ("UI toggles", {"toggle", "show", "hide", "turn", "switch", "enter", "leave", "invert", "zoom", "fit"}),
    "y": ("copy", {"copy", "yank", "save"}),
    "f": ("find / filter", {"find", "filter", "search", "show", "clear", "hide", "pick", "open", "jump", "toggle"}),
    "s": ("sort", {"sort", "order", "reverse"}),
    "r": ("refresh", {"refresh", "reload", "rescan", "update", "sync", "fetch", "search", "retry", "resync"}),
    "a": ("add / new", {"add", "create", "new", "save", "pair", "start", "accept", "write", "make",
                          "compose", "send", "attach", "connect"}),
    "d": ("delete", {"delete", "remove", "clear", "forget", "dismiss", "kill", "prune", "unpair", "disconnect",
                     "stop", "drop", "reject", "trash", "close", "cancel", "take", "decline", "archive"}),
    "e": ("edit", {"edit", "rename", "pick", "change", "set", "open"}),
    "o": ("open outside", {"open", "run", "show", "browse", "play"}),
    "g": ("go to", {"go", "jump", "switch", "show", "open", "focus", "move", "check"}),
    "m": ("mark", {"mark", "toggle", "pin", "unpin", "star", "unstar", "label", "flag", "move", "set"}),
    ",": ("settings", {"open", "show", "edit", "change", "set", "toggle", "sign", "connect"}),
    "k": ("ask the AI", {"ask", "summarize", "draft", "write", "explain", "show", "open", "talk", "send"}),
}
IRREVERSIBLE = {"delete", "remove", "kill", "archive", "reboot", "lock", "ring", "forget", "unpair",
                "dismiss", "trash", "prune", "power"}


def grammar_warnings(entries):
    """The Space-grammar rules: warnings (failures with --strict)."""
    warn = []
    groups = {(g["source"], g["scope"], key_seqs(g["keys"])[0]): g["name"]
              for g in GROUPS if key_seqs(g["keys"])}
    for (src, scope, seq), name in groups.items():
        if len(seq) == 2 and seq[0] == "Space" and seq[1] in RESERVED:
            meaning = RESERVED[seq[1]][0]
            first = meaning.split()[0].lower()
            if first not in name.lower() and not any(v in name.lower() for v in (RESERVED[seq[1]][1] or ())):
                warn.append(f"{src}/{scope}: group Space {seq[1]} is '{name}', but Space {seq[1]} is reserved for "
                            f"{meaning} in every tool (docs/KEYBINDINGS.md, the Space grammar)")
    for e in entries:
        if e["origin"] != "script":
            continue
        words = e["desc"].split()
        verb = words[0].split("/")[0].lower() if words else ""
        for seq in key_seqs(e["keys"]):
            if len(seq) >= 3 and seq[0] == "Space" and seq[1] in RESERVED and RESERVED[seq[1]][1] \
                    and verb not in RESERVED[seq[1]][1]:
                warn.append(f"{e['source']}/{e['scope']}: {e['keys']} '{e['desc']}' -- Space {seq[1]} is "
                            f"reserved for {RESERVED[seq[1]][0]}")
                break
        # an annotated capital the code never checks (it fires on the lowercase key)
        seqs = key_seqs(e["keys"])
        caps = {t for q in seqs for t in q if re.fullmatch(r"[A-Z]", t)}
        if caps and e.get("path", "").endswith(".py"):
            # Python tools compare key names as string literals: look through
            # the whole package (keymaps often live in their own module).
            body = ""
            for f in Path(e["path"]).parent.glob("*.py"):
                try:
                    body += re.sub(r"#\s*keybind.*", "", f.read_text(errors="ignore"))
                except OSError:
                    pass
            for c in sorted(caps):
                if not re.search(rf"""['"]{c}['"]|\b{c}\b""", body) and re.search(rf"""['"]{c.lower()}['"]""", body):
                    warn.append(f"{e['source']}/{e['scope']}: {e['keys']} is annotated as '{c}' (Shift+{c.lower()}) "
                                f"but the code only checks '{c.lower()}' -- write the key as it fires")
        # a lone key that does something you can't take back
        if verb in IRREVERSIBLE and any(len(q) == 1 and len(q[0]) == 1 for q in seqs) \
                and not re.search(r"ask|confirm|twice|y confirms|undo|countdown|character|letter|word|digit", e["desc"], re.I):
            warn.append(f"{e['source']}/{e['scope']}: {e['keys']} '{e['desc']}' -- one key does something "
                        f"irreversible: use dd / Space d … with a confirm")
    # `g` bound beside `g g` in the same tool, view and mode
    by = {}
    for e in entries:
        if e["origin"] != "script":
            continue
        by.setdefault((e["source"], e["scope"], e.get("mode")), []).append(e)
    for (src, scope, mode), es in by.items():
        seqs = [(q, e) for e in es for q in key_seqs(e["keys"])]
        whole = {q for q, _ in seqs}
        for q, _ in seqs:
            for n in range(1, len(q)):
                if q[:n] in whole and q[:n] != q:
                    warn.append(f"{src}/{scope}{':' + mode if mode else ''}: {' '.join(q[:n])} is bound and also "
                                f"starts {' '.join(q)} -- the longer one can never be typed")
                    break
    return sorted(set(warn))


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
    warnings = grammar_warnings(entries)
    if STRICT:
        problems += warnings
    elif warnings:
        print(f"keybind-search --check: {len(warnings)} Space-grammar warning(s) (failures with --strict):\n  "
              + "\n  ".join(warnings))
    if problems:
        print("keybind-search --check: FAIL\n  " + "\n  ".join(problems))
        print(f"({summary})")
        sys.exit(1)
    print(f"keybind-search --check: OK ({summary})")


def main():
    args = sys.argv[1:]
    if not args:
        run_panel()
    elif args[0] == "--tmux-fzf":
        run_tmux_fzf(args[1] if len(args) > 1 else None)
    elif args[0] == "--list":
        rest = args[1:]
        keys = None
        if "--keys" in rest:
            i = rest.index("--keys")
            keys = rest[i + 1] if i + 1 < len(rest) else ""
            rest = rest[:i] + rest[i + 2:]
        run_list(rest[0] if rest else None, keys)
    elif args[0] == "--groups":
        run_groups()
    elif args[0] == "--check":
        global TMUX_CONF, STRICT
        rest = args[1:]
        if "--strict" in rest:
            STRICT = True
            rest.remove("--strict")
        if len(rest) > 1 and rest[0] == "--tmux-conf":
            TMUX_CONF = os.path.expanduser(rest[1])
        run_check()
    elif args[0] == "--json":
        json.dump(all_entries(), sys.stdout, indent=1)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
