# Man Page Pipeline: tool change to man.tcos.us

The end-to-end path a change travels, from editing a `hee-*` tool to that
tool's page being readable on man.tcos.us.

Traced 2026-08-31. Stages 1-4 are real and automated. **Stage 5 is manual and
partly undefined** -- that gap is the most important thing in this document,
and it is written down rather than guessed at.

## The stages

| # | Stage | How | State |
|---|---|---|---|
| 1 | Create or change a tool | `tooling/bin/hee-*` | ✅ `OK` defined |
| 2 | Write its help text | the tool's own `help` output | ✅ `OK` defined |
| 3 | Generate pages | `hee gen-manpages` | ✅ `OK` automated |
| 4 | Commit and land | PR into `main` | ✅ `OK` defined |
| 5 | Content reaches prod | manual, undocumented | ❌ `CRITICAL` gap |
| 6 | Lab renders it | automatic, no promotion step | ✅ `OK` see below |

## 1. Create or change a tool

Tools live in `tooling/bin/hee-*` and are invoked as `hee <tool>`.

Two rules govern what you write:

- **Extend, never one-off.** Run `hee list` and find the tool this belongs
  to; add a subcommand to it. A new top-level `hee-<cmd>` is a last resort.
- **Start at the least capable language that does the job**, and graduate
  only when actually outgrown: `library/bash/*.shfn.bash` (sourced function)
  to `tooling/bin/*` sh to `*.py` to a `hee` subcommand to Go/Rust. Keep the
  tool thin and put logic in `library/` where it is testable.

## 2. Help text is the man page

**This is the stage most easily missed.** `hee-gen-manpages` does not read a
separate document. It runs each tool's own help and captures the output. So:

> A tool's help text *is* its man page. Help quality is documentation
> quality, and a tool whose help is broken publishes its breakage.

The failure is not hypothetical. Measured 2026-08-31, 30 of 37 published
pages contain captured *run output* instead of documentation, because those
tools ran instead of printing help. The published `hee-check` page reads:

    find: unknown predicate '--help/prompts'
    OK: basic HEE boundary checks passed for --help

That is the generator faithfully capturing a tool that treated `--help` as a
path to check. Fix the tool's help and the page fixes itself.

Every tool must accept `help`, `--help` and `-h`; help applies to the verb to
its left; and nothing to the right of the help token may be executed.

## 3. Generate

    hee gen-manpages

Writes `man/tools/<tool>.1.md` for every tool, plus `man/tools/README.md` as
an index, and converts to roff (`man/tools/<tool>.1`) when `pandoc` is
present.

**Where it writes.** The generator changes directory to *its own repo root*
before writing, so it always writes to that repo's `man/tools/` no matter
where you invoke it from. On a machine where `hee` is a symlink into a
checkout, that resolves through the symlink to the real checkout, not to
wherever you are standing.

This used to be genuinely hard to see: the tool printed relative paths after
having changed directory, so the output named files that did not exist
relative to the caller. It now prints the absolute target directory up front
(https://github.com/Twin-Cities-Open-Systems/human-execution-engine/pull/470).

**`help` works on both call paths.** `hee gen-manpages help` and
`hee-gen-manpages help` both print usage. Previously only the dispatcher form
did; invoking the binary directly with the bare word `help` regenerated every
page instead of printing help, which is a surprising thing for a help request
to do (https://github.com/Twin-Cities-Open-Systems/human-execution-engine/issues/471).

**Audit help across the fleet** with `hee check cli`, which runs every tool's
help from a temporary directory and reports what is broken. Since help text
is what becomes the man page (stage 2), that audit is also a documentation
audit.

## 4. Commit and land

The generated artifacts are tracked in git under `man/tools/`. Commit them
with the tool change and land them through a PR like any other change.

**Never hand-edit a generated `.1` or `.1.md`.** Fix the tool's help and
regenerate. Hand-editing is how the divergence in the next section started.

## The two-source divergence

There are two copies of the same pages, and the stale one is the one being
served:

| Path | Files | Last generated | Published? |
|---|---|---|---|
| `man/tools/` | 56 | current | ❌ no |
| `man/` (root) | 9 | 2026-08-26 | ✅ **yes** |

`hee-gen-manpages` only ever writes `man/tools/`. The nine files at `man/`
root are orphans: nothing regenerates them, and they are what reaches prod.

Settled by evidence, not inference. The live `hee.txt` documents six
subcommands that do not exist -- `ls`, `fileident`, `pathcheck`, `http404`,
`uiboss`, `serve`. Every one of those strings is present in `man/hee.1` and
absent from `man/tools/hee.1`. The published page is the root copy.

## 5. Reaching prod -- the gap

**man.tcos.us** is a droplet (159.65.46.8) running gophernicus on port 70
with nginx in front, serving `/var/www/man` over HTTPS and proxying
`/gopher/` to the local gateway on `:8070`. That is what produces the
`https://man.tcos.us/gopher/0/<tool>.txt` route.

The repo holds only that host's *configuration* --
`fleet-ops/hosts/man-tcos-us/` contains `gophermap`, `nginx-default.conf` and
`gopher2html-man.py`. It contains **no `.txt` content and no deploy script**,
and unlike its sibling hosts it has no `README.md`.

How page content gets from this repo onto that droplet is **not defined
anywhere in any repo**. Searched: no CI workflow, no systemd timer, no
rsync/scp target, no hee tool. The sibling gateway host records its own
process as "No CI/CD wiring -- manual (`pct push` from the pve host)", and
haproxy's own configuration notes that man.tcos.us's content "lives on Gopher
on a box this session has no SSH access to."

So the honest statement is: **stage 5 is a manual step performed out of band,
by an unrecorded process, onto a host the automation cannot reach.** It is
not documented because it was never written down, and this document does not
invent one.

Two consequences worth stating plainly:

- **The gophermap is hand-maintained and has drifted.** It advertises 38
  entries including `uiboss`, which is not a tool, and omits 17 tools that do
  exist. Those 17 are exactly the pages that render `Error: File or directory
  not found!`.
- **Freshness is unbounded.** With no automation there is no cadence, and a
  page can be arbitrarily stale. The root `man/hee.1` has been wrong since
  2026-08-26.

## 6. Lab does not promote to prod

A natural assumption is that content is staged on man.lab.tcos.us and
promoted to man.tcos.us. **That is backwards.**

**man.lab.tcos.us** is a dedicated Proxmox container (vmid 109,
`tcos-gopher-gateway`, 10.0.0.172), reached through haproxy's
`be_gopher_gateway` backend. It runs `gopher2html-man.py`, which renders
*live* gopher content as HTML. It holds no content of its own.

Lab is a **downstream view of prod**, not an upstream staging area. There is
no lab-to-prod promotion step for man pages, and nothing to add one to.
Publishing to lab is not a stage in this pipeline because lab has nothing to
publish to.

## Verifying a published page

Do not trust the HTTP status code. The gateway returns **200 for pages that
do not exist**, with `Error: File or directory not found!` in the body:

    curl -s https://man.tcos.us/gopher/0/hee-not-a-real-tool.txt  # HTTP 200

Check the body. A real page contains a `SYNOPSIS` or `DESCRIPTION` section; a
missing one contains `File or directory not found`; a stale one contains the
tool's run output instead of prose.

## Known gaps

Filed and tracked rather than left in a transcript:

- Stage 5 is manual and undocumented, onto an unreachable host.
- `man/` root and `man/tools/` are two copies of the same pages; the stale
  root copy is the published one.
- The gophermap is hand-maintained and has drifted from the real tool list.
- `fleet-ops/hosts/man-tcos-us/` has no `README.md`, unlike its siblings.
