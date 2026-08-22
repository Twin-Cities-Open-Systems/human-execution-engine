# `hee-ticket` — real run

Real trigger, 2026-08-21: "we need a workflow for that... internal
system" — `./hee ticket -new 'perm change for oper/agent@host:/foo/bar'`.
Dogfooded with that exact example, not a synthetic one — including a
real footgun found along the way (see below), same idea->footgun->dogfood
pipeline this tool's own `stage` field now tracks.

```
$ ./hee ticket -new 'perm change for oper/agent@host:/foo/bar'
hee-ticket 0001: perm change for oper/agent@host:/foo/bar
  stage: idea
  .hee/tickets/0001.yaml

$ ./hee ticket -advance 0001
hee-ticket 0001: idea -> footgun

$ ./hee ticket -advance 0001
hee-ticket 0001: footgun -> dogfood

$ ./hee ticket -advance 0001
hee-ticket 0001: already at final stage (dogfood), nothing to advance to

$ ./hee ticket -list
0001  [open]  (dogfood)  perm change for oper/agent@host:/foo/bar  (2026-08-22T01:07:41Z)

$ cat .hee/tickets/0001.yaml
id: '0001'
created_at: '2026-08-22T01:07:41Z'
description: perm change for oper/agent@host:/foo/bar
status: open
stage: dogfood
stage_history:
- stage: idea
  at: '2026-08-22T01:07:41Z'
- stage: footgun
  at: '2026-08-22T01:07:41Z'
- stage: dogfood
  at: '2026-08-22T01:07:41Z'
```

## A real footgun this tool hit on itself

First version shipped `-advance` in the docstring/usage text but never
actually registered it as an `argparse` argument — caught immediately
by running it for real, not by code review:

```
$ ./tooling/bin/hee ticket -advance 0001
usage: hee-ticket [-new DESCRIPTION] [-list]
hee-ticket: error: unrecognized arguments: -advance 0001
```

Fixed, re-verified with the real output above.

## A second, real footgun: `.gitignore` itself

`.hee/tickets/0001.yaml` couldn't be `git add`ed at all initially --
`.gitignore` had `!.hee/spool/**`-style negation patterns meant to
re-include specific `.hee/` subdirectories, but git's own documented
limitation ("It is not possible to re-include a file if a parent
directory of that file is excluded") means those negations never
actually worked. `.hee/spool/` and `.hee/evidence/` are only tracked
today because their files were force-added once, before anyone hit
this. Real fix: stopped excluding `.hee/` broadly at all -- only
`.hee/notes/` (genuinely local-only, confirmed untracked) is excluded
now; `spool/`, `evidence/`, `tickets/` are untracked-by-default like
anything else not listed.

## Explicitly not built here

- Structured target parsing (`oper/agent@host:/foo/bar` as a real
  namespaced value, the way `hee-stat`'s `gh/OWNER/REPO` is) — the
  description is free text for now. Worth revisiting once the
  notation itself proves out across more than one example.
- Status transitions beyond `open` (no `-close` yet).
- Anything resembling GitHub Issues' real feature set (labels,
  cross-references, Projects). This is the smallest real step, not a
  replacement — see [`primitives#5`](https://github.com/Twin-Cities-Open-Systems/primitives/issues/5)
  for the real, larger, not-yet-decided question this is one step
  toward answering, not a decision that it's the answer.
