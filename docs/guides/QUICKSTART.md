# Quick start

Every block below is real output, captured on 2026-09-06 and pasted, not
typed. Where a tool refused to do something, the refusal is shown, because
the refusal is usually the point.

## Try it without touching your machine

Nothing here needs to be installed. The tools run from the checkout, and
`man` finds the pages the moment `MANPATH` points at them. So the honest
first step is a directory you will delete:

```sh
$ d=$(mktemp -d)
$ git clone -q https://github.com/Twin-Cities-Open-Systems/human-execution-engine "$d/hee"
$ cd "$d/hee"
$ export PATH="$PWD/tooling/bin:$PATH" MANPATH="$PWD/man/tools:"
$ hee ver | head -1
✅ OK bash: 5.2.21  [self]
$ man -w hee-check
/tmp/tmp.k3x9Qm/hee/man/tools/man1/hee-check.1
$ cd /; rm -rf "$d"
```

That was run in a clean environment with an empty `$HOME`. After the
`rm -rf`, `$HOME` still had zero entries. Nothing was written anywhere but
the directory you chose, and it is gone.

The trailing colon in `MANPATH="...:"` matters: it appends the system's own
manpath, so `man ls` keeps working. Without it you get only ours.

## Or keep a checkout and still write nothing

Same two exports, in your own clone, for this shell only. Close the shell
and it is as if nothing happened:

```sh
$ cd ~/git/human-execution-engine
$ export PATH="$PWD/tooling/bin:$PATH" MANPATH="$PWD/man/tools:"
```

## Make it stick, with a matching undo

Only when you have decided to. The `dotfiles` repo's Makefile registers
the man pages with `man(1)` by writing one line to `~/.manpath`, and the
undo backs that file up before touching it:

```sh
$ cd ~/git/dotfiles
$ make manpath              # writes MANDATORY_MANPATH lines to ~/.manpath
$ make uninstall-manpath    # copies ~/.manpath to ~/.manpath.bak, then removes them
```

`make install` and `make uninstall` do the same for the dotfiles themselves.
Every target says what it wrote. None of them is run for you by anything in
this repository -- a sysadmin's dotfiles are theirs.

A container image for the throwaway tier is planned and does not exist yet.
When it does, it will be listed here; until then, `mktemp -d` is the image.

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

That is a real answer: those example images predate stamping. This one was
generated for this guide by meme-factory, which stamps as it renders, and
its job file sits beside it in the repo:

```sh
$ hee exif read docs/guides/examples/quickstart-tile.png --provenance
tool: meme-factory/tile
commit: eabdc39
job: human-execution-engine/docs/guides/examples/quickstart-tile.png.job.json
job_sha256: b05434bd8740e2779d77c012a5f5cf75f19906c084c3cafd9011fc3a2ddf1aee
shape: tile
og_for: https://github.com/Twin-Cities-Open-Systems/human-execution-engine/blob/main/docs/guides/QUICKSTART.md
page: root
owner: Twin Cities Open Systems
host: github.com
signed: kiosk-claude-84f0007d_1:0.0
```

It is YAML, so `yq` reads it without a parsing step:

```sh
$ hee exif read docs/guides/examples/quickstart-tile.png --provenance | yq '.tool, .commit'
meme-factory/tile
eabdc39
```

Every line of that is a claim the file makes about itself, and `job_sha256`
is how you check the claim: hash the job file it names and compare.

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

- Every tool's help is its man page. The second form works anywhere; the
  first needs `MANPATH` from one of the tiers at the top:

  ```sh
  $ hee check help
  $ man hee-check
  ```

- Every tool with its one-line meaning, and the same list at the prompt:

  ```sh
  $ hee list
  $ hee <TAB>
  ```

- The rules an agent reads at session start: `prompts/PROMPTING_RULES.md`.
- Why any of this exists: the README's problem statement, and
  `docs/REFERENCES.md` for the twenty-year lineage.
