# AI tools

Vayu gives AI agents (Claude Code, Codex, Aider, or anything that can run a
shell command or speak MCP) a set of desktop tools of their own, so working
with an agent doesn't mean copying commands back and forth. Every tool keeps
you in charge: an agent can ask, only you can approve.

The tools live in [`ai/`](https://github.com/Theyashsawarkar/vayu/tree/development/ai)
and are installed root-owned by `~/dotfiles/ai/apply.sh` (part of
`install.sh`; `vayu-verify` checks them).

## vayu-elevate: root commands, approved once

When an agent needs something done as root (install a package, enable a
service, edit a file under `/etc`), it sends the commands to `vayu-elevate`
instead of asking you to paste them into a terminal. A window opens on your
desktop:

- every command, exactly as it will run, under the agent's reason for it;
- a checkbox on each: untick anything you don't want run;
- one password field: your password, typed once, for all the ticked commands.

Press **Run** (or Enter in the password field). The ticked commands run as
root, one after another, stopping at the first one that fails, and each
card shows its result. The agent gets everything back: which commands you
approved or declined, and each one's exit code and output.

| Key | Does |
|---|---|
| `Enter` (in the password field) | Run the ticked commands |
| `Esc` | Deny the whole request (nothing runs) |
| `Space` | Tick or untick the focused command |

A request you don't answer expires after 10 minutes and counts as denied.
Three wrong passwords end it too. Closing the window denies it.

**What's recorded:** every command that ran as root, with its exit code, in
`/var/log/vayu-elevate.log` (root-only, so the agent can't edit it); every
request, including denied ones, in `~/.local/state/vayu-elevate/requests.jsonl`.

```sh
sudo tail -n 20 /var/log/vayu-elevate.log | jq .
tail -n 5 ~/.local/state/vayu-elevate/requests.jsonl | jq .
```

## For agents: using vayu-elevate

Send a JSON request on stdin. It blocks until the user answers (up to 10
minutes), then prints a JSON result.

```sh
vayu-elevate <<'EOF'
{
  "requester": "Claude Code",
  "reason": "Install Docker and start it on demand, as you asked.",
  "commands": [
    {"cmd": "pacman -S --needed --noconfirm docker", "why": "Install Docker"},
    {"cmd": "systemctl enable --now docker.socket", "why": "Start Docker when something connects to it"}
  ]
}
EOF
```

One-off form: `vayu-elevate --requester "Claude Code" --why "Reload udev rules" --cmd "udevadm control --reload"`
(repeat `--why`/`--cmd` pairs for more). `vayu-elevate --schema` prints the
request and result JSON Schema.

**Rules for the commands:**

- Each runs as root with `bash -c`, from `/`, with **no stdin and no tty**.
  Anything that prompts will fail or hang until its 30-minute limit: use
  `pacman --noconfirm`, `apt -y`, `cp -f` and the like.
- They run in order and stop at the first non-zero exit; the rest are
  reported as `skipped`.
- Every command needs a `why`: one plain line the user decides from.
- At most 50 commands, 8000 characters each. Control characters and
  invisible Unicode (bidi overrides, zero-width) are rejected, so what the
  user reads is what runs.
- Paths: there's no `~` for your user (it's root's environment). Write
  `/home/<user>/...` in full.

**The result:**

```json
{
  "status": "completed",
  "message": "Ran the approved commands.",
  "approved": [0, 1],
  "declined": [],
  "results": [
    {"index": 0, "command": "pacman -S --needed --noconfirm docker", "why": "Install Docker",
     "decision": "approved", "state": "ok", "exit_code": 0, "stdout": "...", "stderr": "",
     "duration": 14.2, "timed_out": false, "truncated": false},
    {"index": 1, "command": "systemctl enable --now docker.socket", "why": "...",
     "decision": "approved", "state": "ok", "exit_code": 0, "stdout": "", "stderr": "Created symlink ...",
     "duration": 0.4, "timed_out": false, "truncated": false}
  ]
}
```

| `status` | Meaning |
|---|---|
| `completed` | The user approved at least one command and they ran. Check each result's `state`. |
| `denied` | The user pressed Deny, Esc or closed the window. Nothing ran. |
| `timeout` | No answer within 10 minutes. Nothing ran. |
| `auth_failed` | Wrong password three times. Nothing ran. |
| `error` | Bad request or the tool itself failed; see `message`. |

Each result's `state`: `ok`, `failed` (non-zero exit), `skipped` (an earlier
command failed), `declined` (the user unticked it), or `not_run`. Output is
capped at 512 KB per stream (`truncated: true` when cut).

Exit codes: `0` everything approved and succeeded, `1` an approved command
failed, `3` nothing ran (denied, timeout, wrong password), `4` some commands
declined and the rest succeeded, `2` bad request or tool error.

**Be a good citizen:** ask for exactly what's needed, explain each command
honestly, don't re-send a denied request unless the user asks, and treat a
declined command as the user's answer.

### Over MCP

`vayu-elevate --mcp` is an MCP server (stdio) with one tool,
`request_root_commands`, taking the same request object and returning the
result as both text and `structuredContent`.

Claude Code:

```sh
claude mcp add --scope user vayu-elevate -- vayu-elevate --mcp
```

Any client with an `mcpServers` config (Claude Desktop, Cursor, ...):

```json
{
  "mcpServers": {
    "vayu-elevate": {"command": "/usr/local/bin/vayu-elevate", "args": ["--mcp"]}
  }
}
```

The call blocks until the user answers, up to 10 minutes. If your client
times out tool calls sooner, raise its limit (Claude Code: the
`MCP_TOOL_TIMEOUT` environment variable, in milliseconds).

### Letting agents know

Claude Code on this desktop is told about `vayu-elevate` in the global
`~/.claude/CLAUDE.md` (the stowed `claude/` package). For other agents, add
the same few lines to their global instructions file (Codex:
`~/.codex/AGENTS.md`; Gemini CLI: `~/.gemini/GEMINI.md`):

```markdown
- Commands that need root: don't ask me to paste sudo commands. Send them to
  `vayu-elevate` (JSON on stdin: requester, reason, commands: [{cmd, why}];
  see `vayu-elevate --help`). I approve them in a window; you get the results.
```

## Security: what it does and doesn't protect against

`vayu-elevate` is a consent gate: nothing runs as root unless you see it and
type your password.

- **The agent never sees your password.** It's typed into the approval
  window, a separate process the agent didn't start (a transient systemd
  user service) and can't inspect (marked non-dumpable).
- **What runs is what you saw.** The window and the root-side runner are
  root-owned files the agent can't edit; the window keeps the request in
  memory once shown; your own GTK styling can't hide part of it; requests
  with invisible or direction-changing characters are refused.
- **No leftover access.** sudo is run with `-k`, so no cached credentials
  remain for anything else to use.

What it can't do: protect you from a program that is actively malicious
and already running as your user. Such a program could draw a lookalike
window to collect your password; that's true of every password prompt on
a Linux desktop. Use it with agents you trust to ask honestly, and read
the commands before you approve them.

More detail, including the exact flow: [`ai/README.md`](https://github.com/Theyashsawarkar/vayu/blob/development/ai/README.md).
Problems: see "AI tools" in [Troubleshooting](TROUBLESHOOTING.md).
