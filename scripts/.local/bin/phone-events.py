#!/usr/bin/env python3
"""Phone events -> notifications, for KDE Connect on sway (systemd user unit
phone-events.service, started by sway after kdeconnect.service).

Outside Plasma, KDE Connect is silent about three things this makes visible:

  Files from the phone   the share plugin reports finished transfers only to
                         Plasma's job tracker ("Failed to check which JobView
                         API is supported" here), so a received file just
                         appeared in ~/Downloads. Watches the share plugin's
                         D-Bus `shareReceived` signal and notifies:
                         click = open it, action menu = show in folder.
  Clipboard from phone   the clipboard plugin silently replaces the laptop
                         clipboard. Watches clipboard changes and, when one
                         carries KDE Connect's signature (see is_from_phone),
                         notifies with a preview and an Undo that restores
                         what the clipboard held before.

  Ring from the phone    KDE Connect's own ring never makes a sound here (a
                         bug, see ring()); this rings instead, with a
                         notification whose click stops it.

It also applies DEVICE_POLICY to every paired phone: laptop -> phone
clipboard sync manual (nothing copied here, passwords included, is pushed
unless sent on purpose), and a ringtone that exists outside Plasma so
"Ring my laptop" is audible.
"""
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

BUS = "org.kde.kdeconnect"
ICON = "/usr/share/icons/candy-icons/apps/scalable/kdeconnect.svg"
KDECONNECT_CONFIG = Path.home() / ".config/kdeconnect"
PREVIEW_LEN = 90


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def notify_with_actions(title, body, actions):
    """actions: [(key, label)], first one is the click (default) action.
    Blocks until the notification is acted on or closed; returns the key."""
    cmd = ["notify-send", "-a", "KDE Connect", "-i", ICON, "--wait"]
    for key, label in actions:
        cmd += ["-A", f"{key}={label}"]
    try:
        return subprocess.run(cmd + [title, body], capture_output=True, text=True,
                              check=False).stdout.strip()
    except OSError:
        return ""


def in_background(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()


def device_name(dev_id):
    out = subprocess.run(["busctl", "--user", "--timeout=3", "--auto-start=no", "get-property", BUS,
                          f"/modules/kdeconnect/devices/{dev_id}",
                          "org.kde.kdeconnect.device", "name"],
                         capture_output=True, text=True, check=False).stdout.strip()
    return out.partition(" ")[2].strip('"') or "phone"


def any_phone_reachable():
    out = subprocess.run(["busctl", "--user", "--timeout=3", "--auto-start=no", "--json=short", "call", BUS,
                          "/modules/kdeconnect", "org.kde.kdeconnect.daemon", "devices",
                          "bb", "true", "true"],
                         capture_output=True, text=True, check=False).stdout
    return '"data":[[]]' not in out and '"data"' in out


# ------------------------------------------------------------------ files
def on_file(dev_id, url):
    name = device_name(dev_id)
    parsed = urlparse(url)
    if parsed.scheme != "file":
        notify_with_actions(f"Link from {name}", url, [("default", "Open")]) == "default" \
            and subprocess.Popen(["xdg-open", url], start_new_session=True)
        return
    path = Path(unquote(parsed.path))
    size = ""
    try:
        n = path.stat().st_size
        size = next(f"{n / d:.1f} {u}" for d, u in ((1 << 30, "GB"), (1 << 20, "MB"), (1 << 10, "KB"), (1, "B")) if n >= d or d == 1)
    except OSError:
        pass
    folder = str(path.parent).replace(str(Path.home()), "~")
    if len(folder) > 32:  # keep "click to open" on screen
        folder = "…/" + path.parent.name
    choice = notify_with_actions(
        f"Received from {name}",
        f"{path.name}  ·  {size}\nin {folder}  ·  click to open",
        [("default", "Open"), ("folder", "Show in folder")])
    if choice == "default":
        subprocess.Popen(["xdg-open", str(path)], start_new_session=True)
    elif choice == "folder":
        subprocess.Popen(["kitty", "--title", "Received files", "-e", "yazi", str(path)],
                         start_new_session=True)


# ------------------------------------------------------ device lifecycle
# pairState: 0 not paired, 1 we asked, 2 the phone is asking, 3 paired.
NOT_PAIRED, REQUESTED, REQUESTED_BY_PEER, PAIRED = 0, 1, 2, 3
pair_states = {}      # dev_id -> last seen pairState
pair_prompts = {}     # dev_id -> (notify-send Popen, notification id) of an open request


def dev_prop(dev_id, name):
    out = subprocess.run(["busctl", "--user", "--timeout=3", "--auto-start=no", "get-property", BUS,
                          f"/modules/kdeconnect/devices/{dev_id}", "org.kde.kdeconnect.device",
                          name], capture_output=True, text=True, check=False).stdout.strip()
    kind, _, value = out.partition(" ")
    if kind == "i":
        return int(value)
    if kind == "b":
        return value == "true"
    return value.strip('"')


def dev_call(dev_id, method):
    subprocess.run(["busctl", "--user", "--timeout=3", "call", BUS, f"/modules/kdeconnect/devices/{dev_id}",
                    "org.kde.kdeconnect.device", method], capture_output=True, check=False)


def simple_notify(title, body, urgency="low"):
    subprocess.run(["notify-send", "-a", "KDE Connect", "-u", urgency, "-i", ICON, title, body],
                   check=False)


def close_pair_prompt(dev_id):
    """Closes the notification and the dialog of an open pair request."""
    prompt = pair_prompts.pop(dev_id, None)
    if not prompt:
        return
    prompt["decided"].set()
    if prompt["notify"].poll() is None and prompt["notif_id"]:
        subprocess.run(["makoctl", "dismiss", "-n", prompt["notif_id"]], check=False)
    if prompt.get("dialog") and prompt["dialog"].poll() is None:
        prompt["dialog"].kill()


def decide_pairing(dev_id, name, prompt, accept):
    """Runs once per request, whichever of dialog/notification answers first."""
    with prompt["lock"]:
        if prompt["decided"].is_set():
            return
        prompt["decided"].set()
    dev_call(dev_id, "acceptPairing" if accept else "cancelPairing")
    if not accept:
        simple_notify("Pairing rejected", f"{name} was not paired")
    close_pair_prompt(dev_id)


def prompt_pairing(dev_id):
    """The phone asked to pair. mako can't draw buttons, so besides the
    notification (click = Accept, Super+Ctrl+a = Reject) a small wofi dialog
    opens with both choices spelled out. Esc on the dialog leaves the
    notification to answer later; either answer closes the other, and both
    close if the phone withdraws the request."""
    name = device_name(dev_id)
    key = dev_prop(dev_id, "verificationKey")
    notify = subprocess.Popen(
        ["notify-send", "-a", "KDE Connect", "-u", "critical", "-i", ICON, "-p",
         "-A", "default=Accept", "-A", "reject=Reject",
         f"{name} wants to pair",
         f"Verification key {key}: check the phone shows the same\n"
         "Click to accept · Super+Ctrl+a to reject"],
        stdout=subprocess.PIPE, text=True)
    prompt = {"notify": notify, "notif_id": notify.stdout.readline().strip(),
              "dialog": None, "decided": threading.Event(), "lock": threading.Lock()}
    pair_prompts[dev_id] = prompt

    accept_label = f"Accept pairing with {name}   (key {key})"
    reject_label = f"Reject pairing with {name}"

    def dialog():
        prompt["dialog"] = subprocess.Popen(
            ["wofi", "--dmenu", "-i", "--lines", "3", "-p", f"{name} wants to pair "],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        choice, _ = prompt["dialog"].communicate(f"{accept_label}\n{reject_label}\n")
        choice = choice.strip()
        if choice == accept_label:
            decide_pairing(dev_id, name, prompt, True)
        elif choice == reject_label:
            decide_pairing(dev_id, name, prompt, False)
        # Esc / closed: the notification is still there to answer.
    in_background(dialog)

    action = notify.stdout.readline().strip()
    notify.wait()
    if action == "default":
        decide_pairing(dev_id, name, prompt, True)
    elif action == "reject":
        decide_pairing(dev_id, name, prompt, False)


def on_pair_state(dev_id, state):
    previous = pair_states.get(dev_id)
    pair_states[dev_id] = state
    name = device_name(dev_id)
    if state != REQUESTED_BY_PEER:
        close_pair_prompt(dev_id)
    if state == REQUESTED_BY_PEER and previous != REQUESTED_BY_PEER:
        in_background(prompt_pairing, dev_id)
    elif state == PAIRED and previous != PAIRED:
        simple_notify(f"Paired with {name}", "Files, clipboard, notifications and remote input "
                      "are ready · Super+Shift+o for the phone picker", "normal")
        # Plugin config dirs appear with the pairing; give them a moment.
        threading.Timer(3, enforce_device_policy).start()
    elif state == NOT_PAIRED and previous == PAIRED:
        simple_notify(f"Unpaired from {name}", "Pair again from the phone, or Super+Shift+o")
    elif state == NOT_PAIRED and previous == REQUESTED_BY_PEER:
        simple_notify("Pairing request expired", f"{name} is not paired")


def on_reachable(dev_id, reachable):
    if not dev_prop(dev_id, "isPaired"):
        return
    name = device_name(dev_id)
    if reachable:
        simple_notify(f"{name} connected", "Super+Shift+o for the phone picker")
    else:
        simple_notify(f"{name} disconnected", "Out of range, KDE Connect closed on it, or another network")


def on_pairing_failed(dev_id, error):
    close_pair_prompt(dev_id)
    simple_notify("Pairing failed", f"{device_name(dev_id)}: {error}", "critical")


SIGNALS = {  # (interface suffix, member) -> handler(dev_id, value)
    ("device.share", "shareReceived"): lambda d, v: in_background(on_file, d, v),
    ("device", "pairStateChanged"): on_pair_state,
    ("device", "reachableChanged"): on_reachable,
    ("device", "pairingFailed"): on_pairing_failed,
}


def parse_arg(line):
    m = re.match(r'\s+(string|int32|boolean) (.*)$', line)
    if not m:
        return None
    kind, value = m.groups()
    if kind == "string":
        return value[1:-1]
    if kind == "int32":
        return int(value)
    return value == "true"


def watch_signals():
    """One dbus-monitor for every KDE Connect signal handled here. All of
    them carry exactly one argument, so the handler runs on that line (a
    per-signal flush, not on the next signal's header)."""
    rules = [f"type='signal',interface='{BUS}.{iface}',member='{member}'"
             for iface, member in SIGNALS]
    while True:
        # stdbuf: dbus-monitor block-buffers into a pipe, so signals sat
        # unread until 4 KB accumulated (found testing with a fake signal).
        proc = subprocess.Popen(["stdbuf", "-oL", "dbus-monitor", "--session", *rules],
                                stdout=subprocess.PIPE, text=True)
        pending = None
        for line in proc.stdout:
            m = re.search(r"path=/modules/kdeconnect/devices/([^/;]+)[^;]*; "
                          rf"interface={re.escape(BUS)}\.([\w.]+); member=(\w+)", line)
            if m:
                handler = SIGNALS.get((m.group(2), m.group(3)))
                pending = (handler, m.group(1)) if handler else None
                continue
            value = parse_arg(line)
            if pending and value is not None:
                handler, dev_id = pending
                pending = None
                try:
                    handler(dev_id, value)
                except Exception as e:  # never let one bad event kill the watcher
                    log("handler failed:", e)
        time.sleep(2)  # dbus-monitor died (session bus restart?): resubscribe


def load_initial_states():
    """Know every device's pair state before the first signal, and surface a
    request that was already pending when this service started."""
    for dev_id, _ in all_devices():
        state = dev_prop(dev_id, "pairState")
        if isinstance(state, int):
            pair_states[dev_id] = None
            on_pair_state(dev_id, state) if state == REQUESTED_BY_PEER else pair_states.__setitem__(dev_id, state)


# -------------------------------------------------------------- clipboard
# KDE Connect sets the clipboard through KSystemClipboard (wlr-data-control),
# which offers exactly these MIME types for plain text. Everything that
# copies on this desktop offers a different set: wl-copy / kitty add
# TEXT/STRING/UTF8_STRING, browsers add text/html etc. Measured, see the
# CHANGELOG entry.
KDECONNECT_TYPES = {"text/plain", "text/plain;charset=utf-8"}


def clipboard_types():
    out = subprocess.run(["wl-paste", "--list-types"], capture_output=True, text=True,
                         check=False).stdout
    return {t.strip() for t in out.splitlines() if t.strip()}


MAX_CLIP_BYTES = 1 << 20  # phone clipboards are text; never slurp a huge one


def clipboard_text(types=None):
    """The clipboard as text, at most MAX_CLIP_BYTES; "" if it holds no text
    (e.g. a copied image) -- read on every clipboard change, so it must stay
    cheap (an uncapped read once pushed this service to a 740 MB peak)."""
    if types is not None and not any(t.startswith("text/") for t in types):
        return ""
    proc = subprocess.Popen(["wl-paste", "--no-newline", "--type", "text/plain"],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    data = proc.stdout.read(MAX_CLIP_BYTES + 1)
    proc.kill()
    proc.wait()
    return "" if len(data) > MAX_CLIP_BYTES else data.decode(errors="replace")


def is_from_phone(types):
    return types == KDECONNECT_TYPES and any_phone_reachable()


def on_phone_clipboard(text, previous):
    preview = " ".join(text.split())
    if len(preview) > PREVIEW_LEN:
        preview = preview[: PREVIEW_LEN - 1] + "…"
    choice = notify_with_actions("Clipboard received from phone",
                                 f"“{preview}”\nalready on your clipboard · Undo restores the previous one",
                                 [("default", "Keep"), ("undo", "Undo")])
    if choice == "undo" and previous is not None:
        subprocess.run(["wl-copy", "--", previous], check=False)
        subprocess.run(["notify-send", "-a", "KDE Connect", "-u", "low", "-i", ICON,
                        "Clipboard restored", "Phone clipboard discarded"], check=False)


def watch_clipboard():
    previous = clipboard_text()
    while True:
        # One line per clipboard change; the content is read here, not by
        # wl-paste's child, so the previous value stays in memory (never
        # written to disk -- it may be a password).
        proc = subprocess.Popen(["wl-paste", "--watch", "echo", "changed"],
                                stdout=subprocess.PIPE, text=True)
        for _ in proc.stdout:
            types = clipboard_types()
            text = clipboard_text(types)
            if os.environ.get("PHONE_EVENTS_DEBUG"):
                log("clipboard change, types:", sorted(types))
            if text and text != previous and is_from_phone(types):
                in_background(on_phone_clipboard, text, previous)
            previous = text
        time.sleep(2)


# ------------------------------------------------------------------- ring
# "Ring my laptop" from the phone. KDE Connect's own ring is broken here: its
# find-this-device plugin deletes its QMediaPlayer on the first
# playingChanged signal, which fires as playback *starts* -- the Qt
# multimedia log shows "Create PlaybackEngine ... Delete PlaybackEngine /
# Free audio output" 0.2 ms apart, so nothing is ever heard. It does open
# the configured ringtone first, and FFmpeg always logs that
# ("Input #0, ogg, from '<ringtone>'"); the ringtone file name is unique to
# this setup, so that log line is the ring request. This then rings for
# real: pw-play of ring_sound() (the user's song, else that ringtone), up to
# RING_MAX_SECONDS, with a notification. Stop it by clicking or dismissing
# the notification, Super+Ctrl+a (kills the player directly, no mako
# involved; see RING_PID_FILE), or Ring again on the phone
# (a second request while ringing = stop). Muted speakers are unmuted for
# the ring and re-muted after.
RING_SONG_DIR = Path.home() / "Music/Ringtones"  # find-my-laptop.<ext>: any song
RING_MAX_SECONDS = 60
# The ringing pw-play's pid, for notification-actions.sh (Super+Ctrl+a).
RING_PID_FILE = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "find-my-laptop.pid"
ring_state = {"player": None}
ring_lock = threading.Lock()


def ring_sound():
    """The user's song if present (~/Music/Ringtones/find-my-laptop.*,
    swappable any time), else the generated phone ring."""
    for f in sorted(RING_SONG_DIR.glob("find-my-laptop.*")):
        if f.suffix.lower() in (".mp3", ".m4a", ".ogg", ".oga", ".opus", ".flac", ".wav"):
            return f
    return RINGTONE


def ring():
    with ring_lock:
        player = ring_state["player"]
        if player and player.poll() is None:
            player.terminate()  # Ring pressed again on the phone: stop
            return
        # --media-role Alarm, not Notification: WirePlumber had restored the
        # Notification role at 0.0002 volume, so the ring played unheard.
        player = subprocess.Popen(["pw-play", "--media-role", "Alarm", "--volume", "1.0",
                                   str(ring_sound())])
        ring_state["player"] = player
    log(f"ring: playing {ring_sound()} (pid {player.pid})")
    # Stop paths that need nothing else to work: the time limit starts now,
    # not once the notification is up, and Super+Ctrl+a kills the player
    # via RING_PID_FILE without asking mako. On 2026-09-29 a ring could not
    # be stopped: no click or Super+Ctrl+a reached this code in 24 s, and
    # the limit only started after the notification, so the only way out
    # was the power key.
    limit = threading.Timer(RING_MAX_SECONDS, lambda: player.poll() is None and player.terminate())
    limit.daemon = True
    limit.start()
    try:
        RING_PID_FILE.write_text(f"{player.pid}\n")
    except OSError as e:
        log("ring: can't write", RING_PID_FILE, e)
    try:
        muted = subprocess.run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], capture_output=True,
                               text=True, check=False, timeout=3).stdout.strip().endswith("yes")
        if muted:
            subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"], check=False, timeout=3)
    except subprocess.TimeoutExpired:
        muted = False
    shown = {}

    def notify_and_stop_on_click():
        # In its own thread: the name lookup asks KDE Connect, busy with
        # the ring request right then, and mako may be slow to answer;
        # neither may hold up the stop paths above.
        name = next((n for _, n in reachable_devices()), "Your phone")
        if player.poll() is not None:
            return
        notify = subprocess.Popen(
            ["notify-send", "-a", "KDE Connect", "-u", "critical", "-i", ICON, "-p",
             "-A", "default=Stop ringing", f"{name} is ringing this laptop",
             "Click to stop · or Super+Ctrl+a · or Ring again on the phone"
             + (" · speakers unmuted for the ring" if muted else "")],
            stdout=subprocess.PIPE, text=True)
        shown["notify"], shown["id"] = notify, notify.stdout.readline().strip()
        log(f"ring: notification {shown['id']} shown")
        if player.poll() is not None:  # the ring ended while it was coming up
            subprocess.run(["makoctl", "dismiss", "-n", shown["id"]], check=False)
        action = notify.stdout.readline().strip()  # clicked, dismissed, or closed by us
        notify.wait()
        if player.poll() is None:
            log(f"ring: notification {action or 'dismissed'}, stopping")
            player.terminate()
    in_background(notify_and_stop_on_click)

    player.wait()
    limit.cancel()
    log(f"ring: stopped after exit code {player.returncode}")
    try:
        if RING_PID_FILE.read_text().strip() == str(player.pid):
            RING_PID_FILE.unlink()
    except OSError:
        pass
    if shown.get("id") and shown["notify"].poll() is None:
        subprocess.run(["makoctl", "dismiss", "-n", shown["id"]], check=False, timeout=3)
    if muted:
        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"], check=False)


def watch_ring():
    marker = RINGTONE.name
    while True:
        proc = subprocess.Popen(["stdbuf", "-oL", "journalctl", "--user", "-u", "kdeconnect.service",
                                 "-f", "-n", "0", "-o", "cat"], stdout=subprocess.PIPE, text=True)
        for line in proc.stdout:
            if marker in line and "Input #" in line:
                in_background(ring)
        time.sleep(2)  # journalctl exited: follow again


def all_devices():
    return devices_where(False, False)


def reachable_devices():
    return devices_where(True, True)


def devices_where(only_reachable, only_paired):
    import json
    out = subprocess.run(["busctl", "--user", "--timeout=3", "--auto-start=no", "--json=short", "call", BUS,
                          "/modules/kdeconnect", "org.kde.kdeconnect.daemon", "devices",
                          "bb", str(only_reachable).lower(), str(only_paired).lower()],
                         capture_output=True, text=True, check=False).stdout
    try:
        ids = json.loads(out)["data"][0]
    except (ValueError, KeyError, IndexError):
        ids = []
    return [(i, device_name(i)) for i in ids]


# ------------------------------------------------------- per-device policy
# Plugin settings every paired phone gets (KDE Connect keeps them per device,
# so a newly paired phone would otherwise start with the defaults):
DEVICE_POLICY = {
    # Laptop -> phone clipboard only when sent on purpose (phone picker):
    # auto-sync pushed everything copied here, passwords included.
    "kdeconnect_clipboard": {"autoShare": "false"},
    # "Ring my laptop" from the phone: the default ringtone is Plasma's
    # Oxygen-Im-Phone-Ring.ogg, absent outside Plasma, so it rang silently;
    # and KDE Connect plays the ringtone once, so a 1.5 s sound is a chirp
    # you'd miss, not a ring. See make_ringtone().
    "kdeconnect_findthisdevice": {"ringtone": None},  # filled in by main()
}
RING_SOURCE = "/usr/share/sounds/freedesktop/stereo/phone-incoming-call.oga"
RINGTONE = Path.home() / ".local/share/sounds/kdeconnect-find-my-laptop.oga"
RING_REPEATS = 12  # x (1.46 s ring + 0.5 s gap) = ~24 s


def make_ringtone():
    """~24 s "find my laptop" ringtone: the freedesktop phone ring repeated
    with short gaps. Generated (not kept in the repo); regenerated if gone."""
    if RINGTONE.is_file():
        return str(RINGTONE)
    RINGTONE.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", RING_SOURCE, "-filter_complex",
         f"[0]apad=pad_dur=0.5,aloop=loop={RING_REPEATS - 1}:size=2e6[a]", "-map", "[a]",
         "-c:a", "libvorbis", "-q:a", "5", str(RINGTONE)],
        capture_output=True, text=True, check=False)
    if r.returncode != 0:
        log("ringtone generation failed, using the short one:", r.stderr.strip())
        return RING_SOURCE
    return str(RINGTONE)


def enforce_device_policy():
    """Applies DEVICE_POLICY to every paired device, live: after writing a
    plugin's config file it emits the same `configChanged` D-Bus signal KDE
    Connect's own settings UI sends, and the running plugin re-reads it.
    It used to restart the daemon instead; each restart dropped the phone's
    connection, and a burst of them left a half-dead session that silently
    ignored everything the phone sent. Returns True if anything changed."""
    changed = False
    for dev_dir in KDECONNECT_CONFIG.iterdir() if KDECONNECT_CONFIG.is_dir() else []:
        if not (dev_dir / "config").is_file():
            continue
        for plugin, settings in DEVICE_POLICY.items():
            cfg = dev_dir / plugin / "config"
            text = cfg.read_text() if cfg.is_file() else ""
            missing = {k: v for k, v in settings.items() if f"{k}={v}" not in text.splitlines()}
            if not missing:
                continue
            for k in missing:
                text = re.sub(rf"(?m)^{k}=.*\n?", "", text)
            if "[General]" not in text:
                text = "[General]\n" + text
            lines = "".join(f"{k}={v}\n" for k, v in missing.items())
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(text.replace("[General]\n", "[General]\n" + lines, 1))
            subprocess.run(["busctl", "--user", "emit", f"/kdeconnect/{dev_dir.name}/{plugin}",
                            "org.kde.kdeconnect.config", "configChanged"], check=False)
            changed = True
            log(f"{dev_dir.name}: {plugin} <- {missing}")
    return changed


def main():
    DEVICE_POLICY["kdeconnect_findthisdevice"]["ringtone"] = "file://" + make_ringtone()
    if len(sys.argv) > 1 and sys.argv[1] == "--enforce-device-policy":
        enforce_device_policy()
        return
    enforce_device_policy()
    load_initial_states()
    threading.Thread(target=watch_signals, daemon=True).start()
    threading.Thread(target=watch_ring, daemon=True).start()
    watch_clipboard()


if __name__ == "__main__":
    main()
