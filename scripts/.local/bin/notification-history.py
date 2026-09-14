#!/usr/bin/env python3
"""Notification history viewer for waybar (bell icon, left of the clock).

mako keeps a real history buffer once a notification expires or is
dismissed (history=1, max-history=200 in mako/config -- off by default,
had to be turned on for this to have anything to show). Reads it via
`makoctl history -j`, already sorted newest-first (confirmed directly by
checking real output, not assumed), and shows it as a wofi list -- one
entry per notification with its actual icon, summary, and full body text
visible up front.

Deliberately not built as "hover an entry, see details in a separate
pane" -- wofi's dmenu architecture has no such mechanism (confirmed: no
focus-change hook, no live preview pane), so the closest honest
equivalent is showing everything already, relying on wofi's own label
wrapping (confirmed live: long text wraps across multiple lines rather
than clipping) instead of inventing a fake "focus" reveal that isn't
really there.

Selecting an entry copies its text to the clipboard -- the same pattern
already used elsewhere in this desktop (wofi-calc.sh, keybind-search.py)
rather than being a no-op.
"""
import html
import json
import os
import subprocess
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

ICON_SIZE = 48
FALLBACK_ICON = "dialog-information-symbolic"

_icon_theme = Gtk.IconTheme.get_default()
_icon_cache = {}


def resolve_icon(name):
    """makoctl's app_icon field is a freedesktop icon-theme NAME for most
    calls, or an absolute path for the couple of notify-send calls in
    this desktop that pass an actual image (a fetched wallpaper, a
    screenshot) as their own icon. wofi's img: escape needs a real file
    path either way -- it does not do theme-name lookup itself (confirmed
    directly: asking it to load a bare theme name failed with "Image ...
    cannot be loaded", not assumed from docs). Resolved through the same
    GTK icon theme lookup every themed icon on this system already goes
    through, so it always matches whatever theme is actually configured
    (candy-icons by default) instead of a hardcoded guess at a path."""
    if not name:
        return None
    if name in _icon_cache:
        return _icon_cache[name]
    if name.startswith("/"):
        path = name if os.path.exists(name) else None
    else:
        info = _icon_theme.lookup_icon(name, ICON_SIZE, 0)
        path = info.get_filename() if info else None
    _icon_cache[name] = path
    return path


def get_history():
    try:
        out = subprocess.run(
            ["makoctl", "history", "-j"], capture_output=True, text=True, timeout=5
        ).stdout
        history = json.loads(out)
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return []
    # makoctl's own ordering isn't reliable enough to trust as-is --
    # checked directly rather than assumed: one run came back newest-first,
    # a later one (this exact function, re-tested) came back oldest-first
    # for the same kind of data. `id` increments monotonically per
    # notification regardless, so sorting on it explicitly is what
    # actually guarantees "newest first", not whatever order the command
    # happens to hand back.
    return sorted(history, key=lambda n: n.get("id", 0), reverse=True)


def format_entry(n):
    """Real bug caught by testing the actual round-trip, not assumed from
    "labels wrap" alone: wofi's dmenu mode splits its *input* on newlines
    into separate entries, one per line -- confirmed directly by piping a
    two-line img:...:text: value in and finding only the first line came
    back as its own entry, the second became an unrelated plain-text
    entry with no icon. The wrapping confirmed earlier is real, but it's
    about one long *single* line wrapping at the window edge, not about
    an embedded \\n staying inside one logical entry. So: one line per
    entry, no \\n in the label at all -- summary and body joined with a
    visible separator instead, same pattern already used for docker-
    picker.py's/wifi-picker.py's own single-line info rows, and long
    ones still wrap naturally within that one entry."""
    icon_path = resolve_icon(n.get("app_icon")) or resolve_icon(FALLBACK_ICON)
    summary = html.escape(n.get("summary") or n.get("app_name") or "(no title)")
    body = html.escape((n.get("body") or "").replace("\n", " ").strip())
    text = f"<b>{summary}</b>"
    if body:
        text += f"  --  {body}"
    prefix = f"img:{icon_path}:text:" if icon_path else "text:"
    return f"{prefix}{text}"


def main():
    history = get_history()
    if not history:
        subprocess.run([
            # Absolute path, not a theme name -- mako has no GTK-style
            # theme resolution (see brightness_osd.sh / mako/config for
            # the full story). candy-icons ships no dialog-information
            # icon at all, so this is AdwaitaLegacy's real blue-filled
            # equivalent.
            "notify-send", "-u", "low",
            "-i", "/usr/share/icons/AdwaitaLegacy/48x48/legacy/dialog-information.png",
            "Notifications", "No notification history yet",
        ])
        return

    # Built fresh per entry rather than reused across a dict comprehension
    # over the same list twice -- keeps format_entry() the single place
    # that decides what a row looks like, and the lookup below the single
    # place matching a selection back to its real (unescaped) content.
    entries = [(format_entry(n), n) for n in history]
    lines = [line for line, _ in entries]
    lookup = dict(entries)

    result = subprocess.run(
        [
            "wofi", "--dmenu", "--allow-images", "--allow-markup", "--insensitive",
            "--matching", "fuzzy", "--prompt", "Notification history...",
            "--lines", "10",
        ],
        input="\n".join(lines), capture_output=True, text=True,
    )
    sel = result.stdout.strip()
    if not sel or sel not in lookup:
        return

    n = lookup[sel]
    clip = "\n".join(filter(None, [n.get("summary"), n.get("body")]))
    proc = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE, text=True)
    proc.stdin.write(clip)
    proc.stdin.close()
    subprocess.run([
        # org.kde.plasma.clipboard's own app icon -- a real, light-filled
        # clipboard illustration, not edit-copy-symbolic, which uses
        # `fill:currentColor` and was rendering as good as invisible on
        # this dark notification background (this exact notify-send call
        # is what was reported as "shows the text but not the clipboard
        # icon" -- see brightness_osd.sh / mako/config for the full story
        # on why bare theme names don't work here). candy-icons ships
        # this exact icon under the same name.
        "notify-send", "-u", "low",
        "-i", "/usr/share/icons/candy-icons/apps/scalable/org.kde.plasma.clipboard.svg",
        "Notification (copied)", n.get("summary") or "",
    ])


if __name__ == "__main__":
    sys.exit(main())
