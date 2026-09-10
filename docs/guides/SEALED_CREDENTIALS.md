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

Read the existing recipient list off the file rather than retyping key
ids, then add the new one:

    R=$(gpg --list-packets --list-only ~/.hee/secrets/plex-token.gpg \
        | sed -n 's/.*keyid \([0-9A-F]*\).*/\1/p' | paste -sd,)

    hee cred -seal plex-token -recipients "$R,<the new key id>" \
      -dir ~/.hee/secrets

`-recipients` is **required** — `hee cred -seal plex-token` on its own
exits with `-recipients required`. And `-seal` reads the secret from an
interactive terminal, never a pipe or a script.

The ids that pipeline returns are encryption **subkey** ids, because that
is what a sealed file records. They will not match the primary key ids
`gpg --list-keys` prints, and that is expected — `-recipients` takes
either.

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

## Shell wrappers, and their one hard limit

`tooling/heerc` sources `library/bash/cred.run.shfn.bash`, which provides:

    hee_cred_run <account> <cmd...>            # cmd sees the derived var
    hee_cred_run_as <VAR> <account> <cmd...>   # cmd sees $VAR
    hee_cred_export <account> [VAR]            # prints VAR=... for eval

`~/.bash_aliases` in `dotfiles` builds a per-credential wrapper on top,
pinning the HOME store so trap 1 cannot bite:

    plexrun() { HEE_CRED_DIR="${HOME}/.hee/secrets" hee_cred_run plex-token "$@"; }

That is the shipped definition, and it depends on `hee_cred_run` — a
shell function `heerc` provides. Inside `~/.bash_aliases` that is safe,
because the repo's `.bashrc` sources `heerc` first and the definition sits
behind a `command -v hee_cred_run` guard. **Pasting that line into a shell
whose `.bashrc` does not source `heerc` gives you a function that fails
with `hee_cred_run: command not found`.** Measured on kiosk 2026-09-10 —
and the wrapper is exactly what the operator reached for, so this is the
likely paste. The form that needs nothing but `hee` on `PATH`:

    plexrun() { HEE_CRED_DIR="${HOME}/.hee/secrets" hee cred -run plex-token -exec "$@"; }

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
