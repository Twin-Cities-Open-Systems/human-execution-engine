# Quick start

Every block below is real output, captured on 2026-09-06 and pasted, not
typed. Where a tool refused to do something, the refusal is shown, because
the refusal is usually the point.

## See an object

Every governance record is YAML with a `kind`, a `metadata` block and a
hash-derived identity. `hee print` renders it for a terminal:

```sh
$ hee print hee/registries/party-kind.registry.v1.yaml
apiVersion: hee/v1
kind: Registry
metadata:
  name: party-kind
  description: Authoritative registry of party-kind values -- the taxonomy for
    classifying WHO or WHAT is acting/attesting/participating anywhere in HEE...
  labels:
    hee.object: "true"
    domain: hee
    scope: governance
  ...
```

Anything piped in is rendered the same way. Here the input is a tool's own
output, on a real file in this repo:

```sh
$ hee exif read library/rrr/examples/hee-logo-1024.png --provenance | hee print
# no provenance on hee-logo-1024.png
```

## What am I running on

```sh
$ hee ver
✅ OK bash: 5.2.21  [self]
✅ OK git: 2.43.0  [self]
✅ OK python3: 3.12.3  [self]
⚠️ WARNING jq: 1.7 (binary under-reports: package is 1.7.1-3ubuntu0.24.04.2)
✅ OK rg: 14.1.0  [self]
✅ OK tmux: 3.4  [self]
✅ OK platform: Linux Mint 22.2 (os-release, lsb_release, uname)
```

`[self]` means the version was read from the binary, not a package manifest.
The `jq` line is a real discrepancy the tool caught, left in on purpose.

## Does the repo agree with itself

```sh
$ hee lint
🟢 OK: hee/registries/party-kind.registry.v1.yaml
...
🟢 OK: RESULT fail=0 warn=0

$ hee check all
```

`hee lint` validates every `hee/v1` object, including that each identity
hash reproduces from its declared seed. `hee check all` runs boundary, refs,
locale and signatures. Both exit with Nagios codes: 0 OK, 1 WARNING,
2 CRITICAL, 3 UNKNOWN.

## Does the record agree with the world

The one that earns its keep. Run in a repo that has a `roster.json`:

```sh
$ hee check roster
  🟢 Executive    Spencer Butler     verified   account=exists org=member
  🟢 Leadership   nuc1-claude        inactive   account=missing org=not-member
  🟢 Team         claudeops-j1       inactive   account=exists org=not-member
  🟢 Team         claudesec-j1       departed   account=missing org=not-member
  🟢 Team         claude-intern-j1   proposed   account=exists org=not-member
  🟢 Team         claude-intern-j2   proposed   no github login recorded
  🟢 Contractors  touchy             peer       account=exists org=member
✅ OK roster: every active claim matches a real account and org membership
```

The first time this ran, three of those seven were CRITICAL: the roster
claimed people were active whose accounts had not existed for weeks. That
is what the check is for. An unmeasurable account is UNKNOWN, never
CRITICAL -- a rate limit is not a departure.

## What made this image

Generated images carry their provenance. Ask for it unpacked:

```sh
$ hee exif read library/rrr/examples/hee-logo-1024.png --provenance
# no provenance on hee-logo-1024.png
```

That is a real answer: those example images predate stamping. A stamped one
returns YAML -- `tool`, `commit`, `job`, `owner` and the rest -- that `yq`
reads directly. There is no stamped image in this repository yet to show it
on, so no example is shown.

## Hold a secret without ever pasting it

```sh
# a recipient is a GPG key. GitHub publishes every user's at a fixed URL:
$ curl -s https://github.com/spencerbutler.gpg | gpg --import
$ gpg --fingerprint spencerbutler | grep -A1 '^pub'
      2D990922FB9DCAB3EE405C710C2E2A08D47F2A2B

$ printf 'sk_live_example_not_real\n' | hee cred -seal example.com -recipients 2D990922FB9DCAB3EE405C710C2E2A08D47F2A2B
hee-cred: -seal requires an interactive terminal -- refusing to read a secret from a pipe/redirect/script
```

That refusal is deliberate and is the feature: a secret that can be piped
can be logged, captured in a transcript, or left in shell history. Run it at
a real terminal and it prompts. Then nothing ever prints it:

```sh
$ hee cred -pass example.com -dir .hee/secrets -exec env
hee-cred: no sealed credential at .hee/secrets/example.com.gpg
```

Also a real answer: nothing was sealed above, because the seal refused the
pipe. At a terminal the seal succeeds, and then `-exec` runs the given
command with `HEE_CRED_PASS` set in its environment and nowhere else. The sealed file is GPG to the listed recipients; seal to more
than one, because a secret only one key can open is an outage waiting for
that key to expire.

## Next

- Every tool's `--help` is its man page: `man hee-check`, or `hee check help`.
- `hee list` prints every tool with its one-line meaning; `hee <TAB>` does
  the same at the prompt.
- The rules an agent reads at session start: `prompts/PROMPTING_RULES.md`.
- Why any of this exists: the README's problem statement, and
  `docs/REFERENCES.md` for the twenty-year lineage.
