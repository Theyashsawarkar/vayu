#!/usr/bin/env python3
"""Fuzzy-searchable keybinding reference for the whole desktop, via wofi.

Bound to $mod+Shift+slash in sway/config. Deliberately excludes Neovim --
it already has its own built-in keymap search.

Two live sources, both re-parsed on every invocation rather than kept in a
hand-maintained cheat-sheet file that would inevitably drift out of sync
with the real configs:

  - Sway: ~/.config/sway/config's own `bindsym` lines, paired with the
    comment sitting directly above each one -- this file's own existing
    convention already, not something invented for this script. $mod and
    the vim-style $left/$down/$up/$right variables are expanded to their
    real key names so entries read as actual keys, not sway variable
    names you'd have to already know.
  - Tmux: `tmux list-keys` (the raw, unambiguous form -- explicit -T
    <table> per line) for which key is bound where, cross-referenced with
    descriptions from two places: this repo's own tmux.conf, which now
    gives every custom bind an explicit `-N "note"` (tmux's own built-in
    per-binding description mechanism -- see tmux.conf's own comment on
    this), and tmux's stock built-in notes via `tmux list-keys -N` for
    everything not explicitly customized here.

    Deliberately NOT sourcing key-table info from `list-keys -N` directly:
    its compact view prefixes every single line with "C-a " regardless of
    which table a binding actually lives in -- confirmed root-table binds
    like `-n M-Left` (no prefix needed at all) still render as "C-a
    M-Left" in that view, which would make this tool actively lie about
    whether a key needs the prefix first. The raw `list-keys` dump states
    the table explicitly and is trusted instead; `-N`'s output is used
    only for its description text, on stock bindings this repo hasn't
    given its own note to.
"""
import re
import subprocess
import sys

SWAY_CONFIG = "/home/yash/.config/sway/config"
TMUX_CONFIG = "/home/yash/.config/tmux/tmux.conf"

# Same Catppuccin Mocha palette wifi-picker.py/bluetooth-picker.py already
# use for their own category colors (Sky/Teal/Peach) -- one source tag per
# color, not a semantic reuse of their exact categories (there's no
# "command"-vs-"connectable" distinction here), just the same two hues for
# visual consistency across every wofi popup in this desktop.
SOURCE_COLORS = {
    "Sway": "#89DCEB",  # Sky
    "Tmux": "#94E2D5",  # Teal
}


def parse_sway():
    with open(SWAY_CONFIG) as f:
        lines = f.readlines()

    variables = {}
    entries = []
    in_resize_mode = False
    pending = None

    def is_descriptive(text):
        if not text:
            return False
        if text.endswith(":"):
            return False
        if set(text) <= set("=-#"):
            return False
        return True

    for raw in lines:
        line = raw.strip()

        if line.startswith("set $"):
            m = re.match(r"set\s+(\$\S+)\s+(.+)", line)
            if m:
                variables[m.group(1)] = m.group(2)
            pending = None
            continue

        if line.startswith('mode "resize"'):
            in_resize_mode = True
            pending = None
            continue
        if in_resize_mode and line == "}":
            in_resize_mode = False
            pending = None
            continue

        if line.startswith("#"):
            text = line.lstrip("#").strip()
            pending = text if is_descriptive(text) else None
            continue

        m = re.match(r"bindsym\s+(?:--locked\s+)?(\S+)\s+(.+)", line)
        if m:
            keys, command = m.groups()
            for var, val in sorted(variables.items(), key=lambda kv: -len(kv[0])):
                keys = keys.replace(var, val)
            keys = keys.replace("Mod4", "Super").replace("Mod1", "Alt")
            command = command.strip()
            if pending and command not in pending:
                # Always append the raw command, even under a fresh,
                # one-to-one comment -- not just cosmetic: fuzzy matching
                # is a subsequence match in query order, so "workspace 1"
                # typed in that order wouldn't match an entry whose only
                # "1" appears *before* the word "workspace" (as it would
                # for Super+1 with just "Switch to workspace" and no
                # command shown). Appending "(workspace number 1)" fixes
                # that regardless of whether the comment was written
                # specifically for this line or carried forward across a
                # whole group (e.g. one comment covering all 4 arrow
                # keys, or $mod+v/$mod+b's shared comment that doesn't
                # itself say which is horizontal vs vertical).
                desc = f"{pending} ({command})"
            elif pending:
                desc = pending
            else:
                desc = command
            entries.append({
                "keys": keys,
                "desc": desc,
                "table": "resize mode (Super+Ctrl+r first)" if in_resize_mode else None,
                "source": "Sway",
            })
            continue

        # Any other real config line invalidates a dangling comment that
        # wasn't actually describing a bind (e.g. a comment sitting above
        # a `client.focused` color line, not a bindsym).
        if line and not line.startswith("#"):
            pending = None

    return entries


def parse_tmux():
    try:
        raw_out = subprocess.run(
            ["tmux", "list-keys"], capture_output=True, text=True, timeout=5
        ).stdout
        notes_out = subprocess.run(
            ["tmux", "list-keys", "-N"], capture_output=True, text=True, timeout=5
        ).stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    # Notes this repo gives its own custom binds directly in tmux.conf --
    # authoritative, and keyed by (table, key) rather than just key: an
    # earlier version of this keyed by bare key alone and discovered the
    # hard way that tmux's own copy-mode/copy-mode-vi tables reuse plain
    # letters like "r" for their own unrelated stock bindings (copy-mode's
    # "r" is refresh-from-pane) -- a key-only lookup let this repo's
    # prefix-table "r" (Reload tmux config) note bleed into those and
    # relabel them incorrectly. Table is read from the same line: no `-n`
    # or `-T` present means tmux's own default of the "prefix" table.
    conf_notes = {}
    try:
        with open(TMUX_CONFIG) as f:
            conf_lines = f.readlines()
        for line in conf_lines:
            m = re.match(r"\s*bind(?:-key)?\s+(.*)", line)
            if not m:
                continue
            note_m = re.search(r'-N\s+"([^"]+)"\s*(.*)', m.group(1))
            if not note_m:
                continue
            note, remainder = note_m.groups()
            table = "root" if re.search(r"(^|\s)-n(\s|$)", m.group(1)) else "prefix"
            t_m = re.search(r"-T\s+(\S+)", m.group(1))
            if t_m:
                table = t_m.group(1)
            remainder = re.sub(r"^-T\s+\S+\s+", "", remainder)
            key = remainder.split(None, 1)[0] if remainder.split() else None
            if key:
                conf_notes[(table, key)] = note
    except OSError:
        pass

    # Stock tmux notes -- confirmed empirically (not assumed) that this
    # compact view only ever has real notes for the prefix and root
    # tables, both rendered with the same leading "C-a " token regardless
    # of which of the two a binding is actually on (see the module
    # docstring) -- `tmux list-keys -N -T copy-mode` etc. comes back
    # empty. So this is only ever consulted for those two tables below,
    # never blindly applied across every table the way conf_notes almost
    # was.
    prefix_key = subprocess.run(
        ["tmux", "show-options", "-g", "-v", "prefix"],
        capture_output=True, text=True, timeout=5,
    ).stdout.strip() or "C-a"
    stock_notes = {}
    for line in notes_out.splitlines():
        rest = line
        if rest.startswith(prefix_key + " "):
            rest = rest[len(prefix_key) + 1:]
        parts = rest.split(None, 1)
        if len(parts) != 2:
            continue
        key, note = parts
        stock_notes.setdefault(key, note)

    entries = []
    seen = set()
    for line in raw_out.splitlines():
        m = re.match(r"bind-key\s+(-r\s+)?-T\s+(\S+)\s+(\S+)\s+(.+)", line)
        if not m:
            continue
        _repeat, table, key, command = m.groups()

        # Mouse bindings aren't keybindings -- and their commands are
        # frequently enormous inline display-menu definitions (one ran
        # nearly 2000 characters), which would both clutter this with
        # things nobody's searching for by "key name" and render as one
        # absurd unreadable line in the wofi popup.
        if re.match(r"^(Mouse|Wheel|DoubleClick|TripleClick)", key):
            continue

        dedup_key = (table, key)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        note = conf_notes.get((table, key))
        if note is None and table in ("prefix", "root"):
            note = stock_notes.get(key)
        if note is None:
            note = command.strip()
            if len(note) > 80:
                note = note[:77] + "..."

        display_keys = f"C-a {key}" if table == "prefix" else key
        scope = None if table in ("prefix", "root") else table

        entries.append({
            "keys": display_keys,
            "desc": note,
            "table": scope,
            "source": "Tmux",
        })

    return entries


MAX_DESC_LEN = 78


def format_line(e):
    # wofi has no CSS/config-level ellipsize or wrap for dmenu entries
    # (checked --help and the binary's own exported symbols -- it does
    # call gtk_label_set_line_wrap internally somewhere, but nothing
    # exposes control over it here, and it isn't applying to these
    # entries regardless). Truncating here instead, not just to avoid
    # the popup's right edge overflowing -- a couple of these descriptions
    # are genuinely enormous (the swaynag exit-sway confirmation message
    # is 243 characters end to end), and even if wofi wrapped them
    # instead of overflowing, a giant multi-paragraph entry would be its
    # own readability problem in a quick-reference list. 78 chars keeps
    # every real entry on one line within the 60% window width (measured
    # against the longest ones that still needed to stay intact, like the
    # OSD scripts' full descriptions) with room left for the longest
    # [scope] suffix.
    desc = e["desc"]
    if len(desc) > MAX_DESC_LEN:
        desc = desc[: MAX_DESC_LEN - 1].rstrip() + "…"
    scope = f"  [{e['table']}]" if e["table"] else ""
    # Same Catppuccin Mocha category-color convention wifi-picker.py and
    # bluetooth-picker.py already use (Sky/Teal/Peach) -- this tool had
    # none at all until now, the one wofi popup in this desktop with
    # zero color-coding despite having two clearly distinct categories
    # (Sway/Tmux) to tell apart at a glance. Colors just the source tag,
    # not the whole line like the other two pickers do -- their entries
    # are one free-text label each, this one has structured columns
    # (tag/keys/description/scope) where tinting everything would hurt
    # readability rather than help it.
    source_color = SOURCE_COLORS.get(e["source"])
    tag = f'<span foreground="{source_color}">{e["source"]:5s}</span>' if source_color else f'{e["source"]:5s}'
    line = f"{tag} {e['keys']:22s} {desc}"
    if scope:
        line += f'<span foreground="#FAB387">{scope}</span>'
    return line


def main():
    entries = parse_sway() + parse_tmux()
    if not entries:
        subprocess.run([
            # Absolute path, not a theme name -- mako has no GTK-style
            # theme resolution (see brightness_osd.sh / mako/config for
            # the full story). candy-icons ships no dialog-error icon at
            # all, so this is AdwaitaLegacy's real red-filled equivalent.
            "notify-send", "-u", "critical",
            "-i", "/usr/share/icons/AdwaitaLegacy/48x48/legacy/dialog-error.png", "Keybindings",
            "Couldn't parse any keybindings -- check sway/tmux configs are readable",
        ])
        sys.exit(1)

    menu_input = "\n".join(format_line(e) for e in entries)

    result = subprocess.run(
        [
            "wofi", "--dmenu", "--insensitive", "--matching", "fuzzy",
            "--prompt", "Search keybindings...", "--lines", "12",
        ],
        input=menu_input, capture_output=True, text=True,
    )
    selection = result.stdout.strip()
    if not selection:
        return

    # Deliberately not subprocess.run -- wl-copy sets the clipboard
    # selection immediately (confirmed directly: cliphist picked up a
    # test string the instant it was sent) but the process itself then
    # lingers afterward, since it has to stay alive to keep *serving*
    # that selection to whatever asks for it next. run()/communicate()
    # both block until the child exits, which would hang this script
    # after every single selection for no reason -- Popen without
    # waiting lets it detach and keep running in the background the way
    # it's designed to, exactly like a shell `| wl-copy` pipeline does.
    proc = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE, text=True)
    proc.stdin.write(selection)
    proc.stdin.close()

    subprocess.run([
        # org.kde.plasma.clipboard's own app icon -- a real, light-filled
        # clipboard illustration, not a theme name (see the note on the
        # dialog-error notify-send above for why bare names don't work).
        # candy-icons ships this exact icon under the same name.
        "notify-send", "-u", "low",
        "-i", "/usr/share/icons/candy-icons/apps/scalable/org.kde.plasma.clipboard.svg",
        "Keybinding (copied)", selection,
    ])


if __name__ == "__main__":
    main()
