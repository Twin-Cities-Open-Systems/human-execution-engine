# PDSH + SSH keys + pdcp pitfalls (lab notes)

Recovered from a private working repo (`tcos-plan-private`) 2026-08-24 as
part of the [fleet-ops#272](https://github.com/Twin-Cities-Open-Systems/fleet-ops/issues/272)
recovery epic. Generic sysadmin reference material -- real internal
hostnames/IPs from the original were replaced with placeholders
(`host1`, `10.0.0.1`) below; everything else is unchanged.

## Goal
- Fan-out commands with `pdsh` over SSH from a box that does **not** run sshd.
- Bootstrap SSH keys cleanly; avoid interactive prompts.
- Copy small files (e.g., `~/.config/pdsh/hosts`) with `pdcp`.

## Baseline setup (client-only)
- Needs: `openssh-client`, `pdsh`
- Verify SSH module: `pdsh -L` should show `Module: rcmd/ssh` and `Active: yes`

## Key bootstrap
### Preferred: ssh-copy-id
- Standard: `ssh-copy-id -i ~/.ssh/id_ed25519.pub user@host1`
- If local `~/.ssh/config` forces publickey and blocks password bootstrap, override:
  `ssh-copy-id -i ~/.ssh/id_ed25519.pub -o PreferredAuthentications=password -o PubkeyAuthentication=no user@host1`

### Bulletproof fallback: append via ssh
- Create perms + append idempotently:
  - `ssh user@host1 'umask 077; mkdir -p ~/.ssh; touch ~/.ssh/authorized_keys; chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys'`
  - `cat ~/.ssh/id_ed25519.pub | ssh user@host1 'grep -qxF "$(cat)" ~/.ssh/authorized_keys || cat >> ~/.ssh/authorized_keys'`

## Triage notes (actual failures seen)
### 1) "/usr/bin/sft: No such file or directory"
- Cause: `~/.ssh/config` contained a ScaleFT `Match exec "/usr/bin/sft ..."` block, but `sft` was not installed.
- Fix: guard the Match with a `test -x /usr/bin/sft && ...` so non-ScaleFT boxes do not blow up.

### 2) ssh works with one target string, fails with another
- Example: `ssh -l user 10.0.0.1 uptime` works, but `ssh-copy-id user@10.0.0.1 ...` fails.
- Cause: different host string triggers different `~/.ssh/config` stanzas, different auth, or different ProxyCommand/Match behavior.
- Fix: use the same host token that worked, or inspect:
  `ssh -G user@host1 | egrep -i 'hostname|user|proxycommand|identityfile|preferredauthentications|pubkeyauthentication'`

### 3) pdsh/pdcp default to local username
- If you run as `alice`, pdsh will try `alice@<host>` unless told otherwise.
- Force remote login name: `pdsh -l bob -w host1 'whoami; echo "$HOME"'`

## pdsh usage patterns
- Single host: `pdsh -l user -w host1 'hostname -f && uptime'`
- Many hosts from a local file: `pdsh -l user -w ^"$HOME/.config/pdsh/hosts" 'uptime'`
- Exclude a host (useful if the hostfile includes localhost but you don't want it):
  `pdsh -l user -w ^"$HOME/.config/pdsh/hosts" -x localhost 'uptime'`

## pdcp usage patterns (gotchas + fixes)
### Gotcha A: `pdcp ... :~/.config/...`
- Do **not** prefix remote paths with `:` here; pdcp already knows the remote via `-w`. Use a normal remote path.

### Gotcha B: `~` expands locally
- If you write: `pdcp -l user -w host1 ~/.config/pdsh/hosts ~/.config/pdsh/hosts`, your local shell expands `~` before pdcp runs -- this can accidentally turn the *remote* destination into your own local home path and fail.
- Fix (safe):
  - Create the remote dir first: `pdsh -l user -w host1 'mkdir -p ~/.config/pdsh && chmod 700 ~/.config/pdsh'`
  - Copy using a relative dest (lands under remote `$HOME`): `pdcp -l user -w host1 "$HOME/.config/pdsh/hosts" ".config/pdsh/hosts"`
  - Or keep `~` but prevent local expansion by quoting the dest: `pdcp -l user -w host1 "$HOME/.config/pdsh/hosts" '~/.config/pdsh/hosts'`

### Gotcha C: `-L`
- `pdcp -L` lists modules/info and exits (not a copy). Do not use it for copying.

## Recommended minimal env on the fanout box
`~/.config/pdsh/env.sh`:
```sh
export PDSH_RCMD_TYPE=ssh
export PDSH_SSH_ARGS_APPEND="-oBatchMode=yes -oConnectTimeout=8 -oServerAliveInterval=30 -oServerAliveCountMax=2 -oStrictHostKeyChecking=accept-new"
export WCOLL="$HOME/.config/pdsh/hosts"
```

## Quick verify checklist
- SSH key auth (no prompts): `ssh -o BatchMode=yes user@host1 'echo OK'`
- pdsh fanout: `pdsh -l user -w ^"$HOME/.config/pdsh/hosts" -x localhost 'hostname -f && uptime'`
- pdcp file present: `pdsh -l user -w host1 'ls -l ~/.config/pdsh/hosts && head -n 5 ~/.config/pdsh/hosts'`

## Lessons / guardrails
- Always watch for `~` expansion when the destination is remote.
- Keep "mixed-user" hostfiles separate (or use `-l` + `-x` to avoid localhost/user mismatch).
- If SSH behaves inconsistently, compare `ssh -G` output across host tokens.

## Delta: final checks / gotchas

### SSH auth hygiene
- Confirm a key is actually offered (useful when agent/config is weird):
  `ssh -v host1 |& egrep -i 'Offering public key|Authentications that can continue'`
- Enforce "no prompts allowed" across a fleet: `pdsh -l user -w ^~/.config/pdsh/hosts -x localhost 'true'`

### Hostfile semantics
- Mixed `user@host` entries + `-l someuser` can surprise you.
  - Preferred: one hostfile per login (e.g. `hosts.alice`, `hosts.bob`)
  - Or: always use `user@host` in WCOLL and avoid `-l`.

### known_hosts / fingerprint drift
- If boxes are rebuilt, be ready for "host key changed": `ssh-keygen -R <ip>` / `ssh-keygen -R <hostname>`

### pdcp expectations
- `pdcp` behaves best when remote has pdsh installed too.
- Remember the `~` expansion footgun: don't use an unquoted `~` for a remote dest.

### Network + sshd basics
- On targets, confirm sshd is listening: `pdsh -l user -w ^~/.config/pdsh/hosts -x localhost 'ss -lntp | grep -E ":(22) " || true'`

### Optional QoL
- Speed up fanout with SSH multiplexing: add `-o ControlMaster=auto -o ControlPersist=5m` to the ssh args.
- Cap concurrency if you go wide: `pdsh -f 16 ...` (tune as needed)
