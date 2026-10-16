# Docker vs UFW — what's actually going on, and what to do about it

## The problem, concretely

UFW manages `iptables` rules to control what's allowed in/out of this machine. Docker
**also** manages `iptables` rules directly — for every container you `-p` publish, the
Docker daemon inserts its own `ACCEPT`/DNAT rules straight into the kernel's `filter`
and `nat` tables, in the `DOCKER`, `DOCKER-ISOLATION-STAGE-1`, and
`DOCKER-ISOLATION-STAGE-2` chains.

The catch: those chains are hit by forwarded packets **before** UFW's own rules get a
say. So `sudo ufw deny 8080` does nothing to protect a container you started with
`docker run -p 8080:80 ...` — Docker's own rule already accepted and forwarded that
traffic. This is not a bug in either tool; it's two independent firewall-rule managers
that don't know about each other, and it's a widely-known gotcha, not something
specific to this machine.

## What was actually checked here (2026-08-23)

Before writing anything or suggesting a fix, I checked whether this machine currently
has any real exposure:

```bash
$ docker ps --format 'table {{.Names}}\t{{.Ports}}'
NAMES     PORTS
```

**No containers running, no ports published.** So as of that check, the gap exists in
theory but nothing is actually exposed by it right now. I did not write or run any
`iptables`/`ufw` change at that point — this session has no `sudo` on this machine, so
any firewall rule I wrote could not be tested against a real container, and a rule I
can't verify is worse than a documented, correctly-scoped gap. That's what "explain
what you did" refers to: checked for live exposure, found none, documented the
mechanism instead of guessing at a fix I couldn't verify.

This file is the follow-through: an actual concrete fix, written out so you (with
`sudo`) can apply and test it, rather than just a warning to "be careful."

## The fix has two layers

### Layer 1 — a habit, zero config changes, works today

When you publish a port, bind it to a specific address instead of leaving it open to
the world:

```bash
# Reachable from any interface, any device on the network -- and bypasses UFW:
docker run -p 8080:80 myimage

# Reachable only from this machine -- Docker never touches the external interface:
docker run -p 127.0.0.1:8080:80 myimage
```

`-p 127.0.0.1:HOST_PORT:CONTAINER_PORT` means Docker only binds the host's loopback
interface. Nothing external can reach it no matter what UFW does or doesn't say,
because the port was never opened on a public-facing interface in the first place.
This is free, requires no system changes, and is enough if you never need a container
reachable from another device.

### Layer 2 — actually restrict Docker's forwarding, for when you do need a published port

Docker creates a chain called `DOCKER-USER` specifically for this: it's the one chain
in the whole Docker iptables setup that Docker **guarantees it will never add rules
to or overwrite** — the officially sanctioned place for an admin's own filtering,
evaluated *before* Docker's own accept/forward rules.

`scripts/harden-docker.sh` (in this repo, next to this file) implements a conservative
default: allow established connections and anything from loopback or a private
(RFC1918) LAN range through to published ports, drop new connection attempts from
anywhere else. Read it before running it — it's short and commented line by line.

```bash
sudo bash docs/harden-docker.sh
```

**Important caveats, because I could not test this myself (no root access in this
session):**

- **`DOCKER-USER` gets reset to empty every time the Docker daemon restarts**
  (`systemctl restart docker`, or a reboot) — Docker recreates the chain fresh. The
  script alone does not survive that. `docs/docker-user-rules.service` (a systemd
  drop-in, also in this repo) re-runs the script automatically every time `docker.service`
  starts, so the rule survives reboots — but you need to install it once (see below).
- **Test before you trust it.** After running the script, from *another device* on
  your LAN, start a throwaway container and confirm you can still reach it:
  `docker run --rm -p 8080:80 nginx:alpine`, then try `curl http://<this-machine-ip>:8080`
  from the other device. If your LAN uses a private range outside 10/8, 172.16/12,
  192.168/16 (uncommon, but possible with some routers/VPNs), the script will block
  it — check `ip addr` for this machine's actual LAN IP if that test fails.
- **Rollback is one command**: `sudo iptables -F DOCKER-USER` removes every rule this
  script added and restores Docker's default (unrestricted) behavior.

### Installing the persistence drop-in (optional, only needed if you actually publish ports)

```bash
# run from ~/dotfiles; fills in this checkout's path
sed "s|@DOTFILES@|$PWD|" docs/docker-user-rules.service | sudo tee /etc/systemd/system/docker-user-rules.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable docker-user-rules.service
sudo systemctl start docker-user-rules.service   # applies it immediately too
```

## Quick reference: how to check exposure at any time

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}'   # what's actually published right now
sudo iptables -L DOCKER-USER -n -v                  # what this hardening (if installed) is doing
sudo ufw status verbose                              # what UFW thinks is allowed (irrelevant to docker-published ports unless the above is installed)
```
