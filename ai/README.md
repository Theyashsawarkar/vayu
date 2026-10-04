# ai/ -- tools the desktop gives AI agents

Not a stow package: `./apply.sh` installs everything here root-owned
(needs sudo), so an agent running as your user can't change what these
tools show you or what they run. User-facing docs, with examples for
agents: [`docs/AI-TOOLS.md`](../docs/AI-TOOLS.md) (on the site as
**AI tools**).

## vayu-elevate: root commands with your approval

An agent sends the commands it needs run as root, each with a reason. A
window shows them; you tick the ones to allow and type your password once;
the ticked ones run; the agent gets each command's output and exit code
back as JSON. No more copying sudo commands between the agent and a
terminal.

| File | Installed as | What |
|---|---|---|
| `elevate/vayu-elevate` | `/usr/local/bin/vayu-elevate` | what agents call: validates the request, opens the window, waits, prints the result. `--mcp` serves the same over MCP (stdio) |
| `elevate/dialog.py` | `/usr/local/lib/vayu-elevate/dialog.py` | the approval window (GTK4/libadwaita, Catppuccin Mocha) |
| `elevate/runner.py` | `/usr/local/lib/vayu-elevate/runner.py` | runs the approved commands as root, streams events, writes the audit log |
| (created) | `/usr/local/lib/vayu-elevate/{config,data}/` | empty XDG dirs the window uses instead of yours |

Flow:

1. `vayu-elevate` rejects bad requests: no `why`, more than 50 commands,
   or control/invisible characters (bidi overrides, zero-width) that could
   make the text shown differ from the text run.
2. It writes the request to `$XDG_RUNTIME_DIR/vayu-elevate/<id>/` (0700)
   and starts the window with `systemd-run --user` + `env -i`: a transient
   service, not a child of the agent, with only the variables it needs.
3. The window reads the request once into memory and shows it. You untick
   anything you don't want, type your password, press Run (or Enter).
4. It checks the password with `sudo -S -k true`, then starts
   `sudo -S -k -- python3 -I runner.py`, writing the password and the
   approved commands to its stdin. Nothing is written to disk; `-k` leaves
   no sudo timestamp behind for anyone else.
5. The runner runs each command with `bash -c`, from `/`, no stdin, a
   minimal environment, 30 min max each, stopping at the first failure.
   It appends every command and exit code to `/var/log/vayu-elevate.log`
   (root-only).
6. The window writes `result.json`; `vayu-elevate` prints it and exits
   (0 all ran fine, 1 one failed, 3 nothing ran, 4 some declined, 2 error).

A request expires after 10 minutes (counts as denied). Three wrong
passwords fail it. Closing the window or Esc denies it. Your own log of
every request, including denied ones: `~/.local/state/vayu-elevate/requests.jsonl`.

## Threat model

What it protects against: an AI agent running anything as root without
you seeing exactly what and approving it. Specifically:

- The agent never sees your password (it's typed into a separate process
  the agent didn't start and can't ptrace: `PR_SET_DUMPABLE=0`, and not a
  descendant of the agent).
- What runs is exactly what was shown and ticked: the window holds the
  request in memory, the runner and window are root-owned files, Python
  runs isolated (`-I`, no user site-packages), and user GTK CSS can't hide
  a row (the window uses root-owned XDG dirs).
- No lingering access: `sudo -k` both times, so no cached credentials.

What it can't protect against: a program that is actively malicious and
running as your user. It could, for example, draw a lookalike window to
collect your password, or tamper with the systemd user manager the window
is started from. That's true of every password prompt on a Linux desktop
(polkit's included). Treat the window as a consent gate for agents you
trust to ask honestly, not a sandbox for untrusted code. Read what each
command does before you type your password.

## Rollback

```sh
sudo rm -rf /usr/local/bin/vayu-elevate /usr/local/lib/vayu-elevate
```

(And drop the "Commands that need root" note from `claude/.claude/CLAUDE.md`
so Claude Code stops using it.)
