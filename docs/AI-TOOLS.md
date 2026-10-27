# Tools

Tools the Vayu desktop provides beyond its configs. The first set is for AI
agents. Click a tool in the table to jump to its section.

## AI tools

Vayu gives AI agents (Claude Code, Codex, Aider, or anything that can run a
shell command or speak MCP) desktop tools of their own, so working with an
agent doesn't mean copying commands back and forth. Every tool keeps you in
charge: an agent can ask, only you can approve.

| Tool | What it does | How agents use it |
|---|---|---|
| [anumati](#anumati) | Runs root commands an agent asks for, after you see each one and why, tick which to allow, and type your password once. | `anumati` (JSON on stdin), or the MCP tool `request_root_commands` |
| [ekatva](#ekatva) | Your phone: status, ring, lock, SMS, calls, its clipboard and files; an SMS or a call only after you allow it. | `ekatva mcp` (MCP server), or the `ekatva` command |

Each is its own repository (Vayu's plugin rule), cloned by `install.sh` and
installed root-owned, so an agent can't change what it shows you or what it
runs. `vayu-verify` checks them.

## anumati

**Root commands, approved once.** When an agent needs something done as
root (install a package, enable a service, edit a file under `/etc`), it
sends the commands to [anumati](https://github.com/Theyashsawarkar/anumati)
(अनुमति, "permission") instead of asking you to paste them into a terminal.
A window shows every command and why; you untick what you don't want and
type your password once; the agent gets the results as JSON. It was called
`vayu-elevate` until 2026-10-21, and that name still works (a link).

![The approval window over the desktop: Claude Code asks to run three commands to install Docker, each with its reason and a checkbox, and a password field with Deny and "Run 3 selected"](../assets/elevate.jpg)

| At a glance | |
|---|---|
| Command | `anumati` (JSON on stdin, or `--cmd`/`--why` pairs) |
| MCP | `anumati --mcp`, tool `request_root_commands` |
| Runs as | root, `bash -c`, from `/`, no stdin, 30 min per command |
| Expires | after 10 minutes without an answer (counts as denied) |
| Logs | `/var/log/anumati.log` (root-only), `~/.local/state/anumati/requests.jsonl` |
| In Vayu | cloned to `~/.local/share/anumati`, installed root-owned by its `install.sh` (`install.sh` step "Installing anumati") |
| Docs | the [README](https://github.com/Theyashsawarkar/anumati#readme): the request and result formats, MCP setup, the security model |

Claude Code on this desktop is told to use it in the global
`~/.claude/CLAUDE.md` (the stowed `claude/` package). Problems: the "AI
tools" entries in [Troubleshooting](TROUBLESHOOTING.md).

## ekatva

**Your phone, for agents too.** [ekatva](https://github.com/Theyashsawarkar/ekatva)
(एकत्व, "oneness") links the laptop and your Android phone end to end,
from any network (a Cloudflare quick tunnel when they're apart). Its
`ekatva mcp` server lets an agent check the phone, ring or lock it, read
SMS, use its clipboard and files and keep the laptop awake. Sending an SMS
or placing a call opens an **Allow / Decline** dialog with the number and
the text first.

| At a glance | |
|---|---|
| MCP | `ekatva mcp`; registered with `claude mcp add --scope user ekatva -e EKATVA_AGENT=claude -- ekatva mcp` |
| Tools | `status`, `phone_status`, `phone_ring`, `phone_lock`, `sms_threads`, `sms_read`, `call_hang_up`, `phone_clipboard_get`/`_set`, `phone_files_list`/`_read`, `caffeine_set`, `log_recent`; asking first: `sms_send`, `call_dial` |
| Log | every call is in ekatva's action log as `yash via claude` (`EKATVA_AGENT`); `ekatva undo N` |
| Service | `ekatva.service` (user unit, in `sway-session.sh`'s `UNITS`); the window is <kbd>Super</kbd>+<kbd>o</kbd> |
| Docs | [For AI agents](https://theyashsawarkar.github.io/ekatva/guides/ai-agents/) |

Messages, the phone's clipboard and files come back inside `<untrusted>`
blocks: they were written by other people. The dialog is a consent step,
not a sandbox: an agent with a shell can run `ekatva` itself.
