# Contributing

The org-wide guide covers the mechanics -- forking, the commit subject
form, what review to expect, where to ask:
https://github.com/Twin-Cities-Open-Systems/.github/blob/main/CONTRIBUTING.md.
This file is what is specific to this repository.

## Start without installing anything

The tools run from the checkout. The README's Get started and
[`docs/guides/QUICKSTART.md`](docs/guides/QUICKSTART.md) show a temp
directory, two exports, and `rm -rf` afterward, run for real in a clean
environment. Nothing here writes to your home directory unless you run
`make` targets in the separate `dotfiles` repo yourself, and each of those
has a matching undo.

## Before you push, run what CI runs

```sh
$ hee check all
$ hee lint
$ tooling/bin/hee-index
```

The third regenerates `hee/INDEX.md`. If you added or renamed any
`hee/v1` object and skip it, CI fails on a stale index -- that happened
three times on 2026-09-06 alone. If you changed a tool's `--help`, also run
`hee gen-manpages --write`, because the help *is* the man page and CI
checks they agree.

## What a good PR here looks like

- One concern. A doctrine change and a tooling change are two PRs.
- The body shows what you ran and what it printed. "Verified" without
  output is a claim; output is evidence.
- If you introduce or rename a concept, the name is right or it does not
  ship. Vocabulary is governed -- see the registries under `hee/registries/`
  and the org glossary -- and a term invented inline in one file is how
  drift starts.
- No absolute paths in prose or code. `hee check` flags `/home/<user>/` and
  `/mnt/<name>/`; a path that only means something on one machine is a
  private layout published.

## Changing doctrine specifically

`blueprints/` and `hee/` are authoritative and validated strictly. The
rules that apply there -- non-terminal `result: false`, deterministic
identity, no hand-edited YAML once tooling exists, no shell in YAML -- are
in [`docs/BLUEPRINT_RULES.md`](docs/BLUEPRINT_RULES.md). Read it before
touching those directories; skip it for everything else.

## Two things that are not obvious

**Imports in a MIB are not transitive**, and an imported object keeps the
OID it was defined with. If you touch `mib/`, run `mib/walk` -- it validates
against net-snmp's own parser, which is a different parser from `smilint`.

**A push to a branch is not a landing.** If your PR merges and you push a
follow-up to the same branch afterward, it goes nowhere. Check `headRefOid`
before assuming; it bit this repo twice in one day.
