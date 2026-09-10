# Sealed credentials — handing a secret to a command

## Objective

Get a secret into the one process that needs it, and nowhere else. No
plaintext file, no shell history, no export that leaks into every later
command in the session.

Everything below was measured on live hosts (kiosk, nuc-1) on 2026-09-09
and 2026-09-10. The traps are recorded because each one cost real time
and each one fails in a way that points at the wrong layer.

## The three shapes

A sealed credential is a GPG file under a **store** directory — by
convention `.hee/secrets/<account>.gpg`. `hee cred` opens it and injects
the plaintext into a child process's environment. It never prints the
secret and never writes it to disk.

| Shape | The command sees | Use when |
|---|---|---|
| `hee cred -pass <account> -exec CMD` | `$HEE_CRED_PASS` | the consumer reads a fixed var, or you are piping to something generic |
| `hee cred -run <account> -exec CMD` | a var derived from the account name | the consumer reads a var named after the credential |
| `hee cred -run <account> -as VAR -exec CMD` | `$VAR` | the consumer's var name does not match the account name |

`-run` derives the variable by uppercasing the account and replacing
every non-alphanumeric character with `_`, prefixing an underscore if the
result would start with a digit. So `plex-token` becomes `PLEX_TOKEN`,
which is exactly what `hee-scrob` reads:

    hee cred -run plex-token -exec hee scrob

`-pass` and `-run` both require `-exec`. There is no form that prints the
secret, deliberately — a secret on stdout is a secret in a scrollback
buffer, a tmux capture, and whatever the operator pastes next.

## Trap 1 — the store is relative to your current directory

`-dir` defaults to `.hee/secrets`, a **relative** path. It resolves
against wherever you happen to be standing.

This is the single most confusing failure in the system, because it
produces a credential that works and then stops working with no change to
anything:

    ~ $ hee cred -run plex-token -exec sh -c 'echo len=${#PLEX_TOKEN}'
    len=20
    ~ $ cd git/human-execution-engine
    ~/git/human-execution-engine $ hee cred -run plex-token -exec true
    hee-cred: no credential ...

Nothing broke. The first command found `~/.hee/secrets` because `~` was
the current directory; the second looked in the repo's own store, which
holds different accounts.

The relative default is intentional — a repo carries its own store, so a
deploy credential lives beside the thing it deploys and cannot be
confused with another repo's. But it means **a credential in the HOME
store must have its directory named explicitly**:

    HEE_CRED_DIR="$HOME/.hee/secrets" hee cred -run plex-token -exec hee scrob

`HEE_CRED_DIR` is deliberately **not** set in `tooling/heerc`. Setting it
globally would override every per-repo store at once and silently point
repo tooling at the wrong directory — the opposite of the isolation the
relative default buys.

## Trap 2 — recipients live in the file, not in your keyring

A sealed file is encrypted to a fixed list of GPG keys chosen when it was
sealed. Copying the file to another host does not make that host able to
open it. Re-sealing it on a host that *can* open it does not help either
until the **new file** reaches the host that could not.

Measured on nuc-1: `do-token.gpg` was byte-identical to kiosk's copy —
same `sha256sum` — and still failed:

    hee-cred: gpg decrypt failed: gpg: decryption failed: No secret key
      do-token.gpg is sealed to: 7F2480F15809ACD8, 01C9F82A7582A4DC
      This host holds no SECRET key for any of them.

**A matching hash is not evidence a credential works.** It measures
whether two files are the same, which is never the question. The question
is whether *this host* holds a secret key for one of the recipients, and
that is a property of the local keyring, not of the file.

To make a credential openable somewhere new, re-seal it **including the
new key** on a host that can already open it, then copy the result:

    hee cred -seal <account> -recipients <existing-key-id>,<new-key-id>

Keep the existing recipients unless you intend to revoke them. Dropping a
recipient to "clean up" breaks whoever was using it, and the breakage
surfaces somewhere else entirely.

## Trap 3 — `gpg --list-keys` answers the wrong question

`--list-keys` lists **public** keys. It will happily show a recipient key
that this host cannot decrypt with, which reads as "the key is right
here, why is it failing."

    gpg --list-secret-keys

is the one that answers "what can this host actually open." `hee cred`
now says this in its failure message for exactly this reason — the
public/secret confusion cost a full round trip before the message
existed.

## Trap 4 — `printf %q` does not exist in dash

The tempting way to get a secret into the *current* shell is an eval:

    eval "$(hee cred -pass X -exec sh -c 'printf "V=%q\n" "$HEE_CRED_PASS"')"

On Debian and derivatives `/bin/sh` is dash, whose `printf` has no `%q`.
It writes an error to stderr, the command substitution yields nothing,
`eval` runs nothing, and the variable ends up **silently empty**. The
caller then debugs decryption, because an empty credential looks exactly
like a failed unseal.

`hee_cred_export` in `library/bash/cred.run.shfn.bash` forces bash for
that one step. Prefer `hee_cred_run` regardless — see below.

## Trap 5 — one variable, two credentials

`hee cred -pass` injects **every** sealed credential under the same fixed
name, `$HEE_CRED_PASS`. That is fine until a single tool needs two of
them, and then it is a credential leak rather than a confusion.

`hee-scrob` needs a Plex token to read now-playing, and a Discord webhook
URL to post it. Both invocations were documented; both set the same
variable:

    hee cred -pass plex-token           -exec hee scrob
    hee cred -pass discord-webhook-scrob -exec hee-scrob -discord

`read_token()` read `$HEE_CRED_PASS`, so under the second invocation it
returned the **webhook URL** and sent it to the Plex server as the token.
Measured, same inputs, before and after the fix:

    BEFORE: read_token() -> 'https://discord.example.invalid/webhook-proof'
    AFTER:  read_token() -> 'plex-tok-proof'

Plex takes its token in the **query string**, so the leak landed in an
access log:

    /status/sessions?X-Plex-Token=<the discord webhook>

Nothing warned about this. Both halves were individually correct.

**The rule:** read `$HEE_CRED_PASS` only where exactly one credential can
possibly be in it. If a tool handles more than one, give each a name of
its own — `-run <account>` derives one (`plex-token` -> `$PLEX_TOKEN`), or
`-run <account> -as VAR` sets one explicitly. Better still, have the tool
open what it needs itself; see below.

## Prefer a tool that opens its own credential

Every trap above is a caller problem, and each one was found because a
caller got it wrong. The way out is to stop asking callers.

A tool that needs a specific credential already knows which one. Having it
unseal that credential itself removes the whole class:

    hee scrob                      # opens plex-token itself
    hee scrob -discord             # opens discord-webhook-scrob itself

versus what it replaced, which had to be right about the store, the
variable name, and the existence of a wrapper:

    HEE_CRED_DIR="$HOME/.hee/secrets" hee cred -run plex-token -exec hee scrob

Two implementation notes worth copying, both found by measurement:

**Resolve the `hee-cred` binary next to your own file, before `PATH`.**
`PATH` is a property of the calling shell, and the interesting callers —
cron, `ssh host cmd`, irssi's `EXEC` — source no profile. The first cut of
this in `hee-scrob` returned nothing on a host where the credential opened
perfectly by hand, purely because neither `hee-cred` nor `hee` was on
`PATH` there. A hee tool's siblings are in its own directory by
construction, so `Path(__file__).parent / "hee-cred"` needs no `PATH` and
bakes in no absolute path.

**Name the store absolutely, and put a timeout on the unseal.** Falling
through to the cwd-relative default is trap 1 all over again. And gpg can
block on an agent prompt with no terminal to prompt on, so a hung unseal
would hang the IRC client — a timeout that falls through to the token file
is better than a spinner nobody can interrupt.

Keep the environment variable as the first thing checked. An explicit
wrapper should still win, for the operator who wants to pass a different
token for one run.

## Shell wrappers, and their one hard limit

`tooling/heerc` sources `library/bash/cred.run.shfn.bash`, which provides:

    hee_cred_run <account> <cmd...>            # cmd sees the derived var
    hee_cred_run_as <VAR> <account> <cmd...>   # cmd sees $VAR
    hee_cred_export <account> [VAR]            # prints VAR=... for eval

`~/.bash_aliases` in `dotfiles` builds a per-credential wrapper on top,
pinning the HOME store so trap 1 cannot bite. **This is a convenience for
interactive use, not the design** — if you find yourself writing a wrapper
so a tool can find its own credential, fix the tool instead:

    plexrun() { HEE_CRED_DIR="${HOME}/.hee/secrets" hee_cred_run plex-token "$@"; }

**It is a runner, not a printer.** It takes a command:

    plexrun hee scrob
    plexrun sh -c 'echo len=${#PLEX_TOKEN}'

Bare, it has nothing to run and prints its usage line.

### The limit: aliases and functions are interactive-only

Nothing defined in `~/.bash_aliases` exists for a script, for
`ssh host cmd`, for cron, for CI, or for irssi's `EXEC`. If a thing must
work non-interactively it belongs in a `hee-*` tool on `PATH`, not in an
alias file.

There is a second, sharper edge: the wrapper only exists if the shell was
wired for it. Measured on nuc-1, 2026-09-10 — `plexrun` produced nothing
at all, and the reason was not the credential:

    $ grep -c bash_aliases ~/.bashrc   # 0
    $ grep -c heerc ~/.bashrc          # 0

That host's `~/.bashrc` predates both the `heerc` source line and the
alias-file block, so `hee_cred_run` was never defined, the guard around
`plexrun` never fired, and the function was never created. The hee
checkout on that host was current; only the **shell wiring** was stale.
`hee` itself was on `PATH` from `.profile`, which is why `hee cred -run`
worked while the wrapper did not — a split that makes the failure look
like a credential problem.

Diagnose it in one command before assuming anything about the secret:

    type plexrun

`not found` means the shell wiring, not the credential. Install the
dotfiles on that host to fix it.

## Seal to who needs it, not to everyone

The instinct after a credential fails on one host is to make every
credential openable on every host. Resist it.

Byte-identical stores everywhere feels tidy and is strictly worse: it
turns any one host's compromise into every credential's compromise. Seal
each credential to the keys that have a concrete reason to open it.

`plex-token` on nuc-1 is worth it — Plex runs there, `hee-scrob` runs
there, the need is real. A DigitalOcean token on a host that never calls
that API is pure blast radius. A credential that will not open on a host
with no use for it is not a bug; it is the boundary working.

## Where credentials actually live

A store is a directory, and there is more than one. This is by design and
it is also a real source of "it works for me":

| Store | Holds |
|---|---|
| `~/.hee/secrets` | personal, cross-repo credentials — needs `HEE_CRED_DIR` |
| `<repo>/.hee/secrets` | credentials scoped to that repo's tooling |
| a deployed service's own directory | credentials that ship with the service |

Machine-bound credentials are invisible until they fail. Three separate
credentials in one session turned out to be openable on exactly one host,
with nothing in any repo recording which host that was. When you seal
something, say where it is openable in the same change.

## See also

- `hee cred --help` — the tool's own manual page, per
  [`prompts/PROMPTING_RULES.md`](../../prompts/PROMPTING_RULES.md) rule 17
- [`library/bash/cred.run.shfn.bash`](../../library/bash/cred.run.shfn.bash)
  — the shell functions, with the dash trap documented at the source
- [`tooling/heerc`](../../tooling/heerc) — what a shell gets for free, and
  why `HEE_CRED_DIR` is not among it
- [`tooling/bin/hee-scrob`](../../tooling/bin/hee-scrob) — the worked
  example of a tool that opens its own credential, including the sibling
  resolution and the unseal timeout
