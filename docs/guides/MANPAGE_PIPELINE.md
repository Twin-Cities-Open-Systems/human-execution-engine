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
| 3 | Generate pages | `hee gen-manpages --write` | ✅ `OK` automated |
| 4 | Commit and land | PR into `main` | ✅ `OK` defined |
| 5 | Content reaches prod | manual, undocumented | ❌ `CRITICAL` gap |
| 6 | Lab renders it | automatic, no promotion step | ✅ `OK` see below |
| L | **Read locally** | `make manpath` in dotfiles | ✅ `OK` see below |

Stage L is a BRANCH, not a step after 6: a page is readable on a workstation
straight from the checkout, without ever reaching prod. Stages 5 and L are
independent, which is why man.tcos.us can be stale while `man hee` is current.

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

**Dry run is the default. `hee gen-manpages` with no arguments writes
nothing.** It generates into a temporary directory, diffs that against what
is committed, and tells you what `--write` would do:

    $ hee gen-manpages
    DRY RUN -- nothing will be written.
    would write to: ~/git/human-execution-engine/man/tools
    staged in:      /tmp/hee-gen-manpages.r5IpqwdL

    pages (man/tools) -- what --write would do:
      2 changed  0 new  0 removed  97 unchanged
      changed: man/tools/hee-gen-manpages.1.md
      changed: man/tools/man1/hee-gen-manpages.1

    Nothing was written. Re-run with --write to apply.

Then apply it:

    hee gen-manpages --write

Writes `man/tools/<tool>.N.md` for every tool, plus `man/tools/README.md` as
an index, and converts to roff (`man/tools/manN/<tool>.N`) when `pandoc` is
present. Authored pages under `man/manN/` are skipped and said so.

The dry run generates for real into a throwaway directory rather than
reasoning about what it would have done, so the two paths cannot disagree:
the diff is computed from the same bytes `--write` writes.

Operator, 2026-09-01: *"I don't like that it just writes files when you run
it without args. those file need to go to a certain spot and oper needs to
know that."* The concern has a documented cost behind it — a bare run of this
tool was once observed installing a pre-commit hook as a side effect of
generating documentation (issue 464), which is why `library/py/hee_toolver`
never invokes a tool without an explicit flag. Same posture as
`hee-reset-tooling` (dry run until `--yes`) and `hee check refs` (reports
until `--fix`).

### The gopher tree

    hee gen-manpages --gopher            # dry run
    hee gen-manpages --gopher --write    # build it

`--write` here **removes the existing tree first** and rebuilds it, which the
tool says out loud before doing it.

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

## L. Reading the pages locally

Nothing is copied or installed. `man` is pointed AT the checkout, so `git pull`
is the update mechanism and there is no second copy to drift.

    cd ~/git/dotfiles && make manpath

That target does three things, and ALL are required:

1. **Registers the path.** Appends `MANDATORY_MANPATH <dir>` lines to
   `~/.manpath` for `<repo>/man` and `<repo>/man/tools`. This is what makes
   `man hee` resolve.

2. **Disables cat-page caching** (`NOCACHE`). `man` writes a compressed "cat
   page" -- its formatted-output cache -- for every page it renders. A
   `MANDATORY_MANPATH` entry has no catdir mapping, so that write fails:

       $ man hee >/dev/null
       gzip: stdout: Bad file descriptor

   On one account this only polluted stderr; on another the page rendered
   EMPTY. Same config, different outcome -- so do not reason about this from a
   single host. `NOCACHE` is manpath(5)'s own answer, and cat pages are only a
   cache; formatting from source is fast.

3. **Builds the mandb index.** This is what makes `man -k hee` / `apropos` /
   `whatis` resolve.

Step 2 is easy to miss because step 1 looks like success. `man <page>` resolves
by WALKING the manpath; `man -k` reads the mandb INDEX and never scans
directories. Register without indexing and you get a confusing half-state: the
pages are installed, and searching for them returns unrelated system pages.

Measured on kiosk 2026-09-01, clean slate, before and after:

    before:  man hee     ->  empty, or `gzip: stdout: Bad file descriptor`
    after:   man hee     ->  53 lines, 0 bytes on stderr

    before:  man -k hee  ->  pam_wheel(8), runxlrd(1), sane-hpsj5s(5)
    after:   man -k hee  ->  hee(1), hee-cred(1), hee-net(1), ... 53 pages

Registering the path WITHOUT steps 2 and 3 produces a half-working install that
looks registered: `man <page>` errors or renders nothing, and `man -k` silently
returns unrelated system pages.

`make manpath` now runs `mandb` itself, so the one command is sufficient. A
failed `mandb` is reported WARNING rather than fatal -- `man` still works, only
search degrades.

### It is per-account, and it had never been run

`~/.manpath` is per-user. On kiosk both `/home/spencer` and `/home/claude` are
mode 0750 and mutually unreadable, so each account must register separately.

As of 2026-09-01 NEITHER had: `make manpath` reported `registered:` rather than
`already registered:` on both. Every generated page in this repo was unreadable
via `man(1)` by anyone until that day, which is worth knowing when judging
whether this pipeline was ever exercised end to end.

### Verifying stage L

    man -w hee              # -> <repo>/man/man1/hee.1, an AUTHORED page
    man -w hee-check        # -> <repo>/man/tools/man1/hee-check.1, generated
    man -w hee-ssh-trust-ca # -> <repo>/man/tools/man8/..., resolves by section
    man -k hee              # apropos finds the set

The third line is the real check on the `man/manN/` layout: `man(1)` honors the
tool's own `# section: N` declaration. A flat `man/*.1` directory cannot be
registered at all, which is why the section directories are structural rather
than cosmetic.

### Known limit of stage L

`man -k` is only as useful as each page's NAME line. Tools whose help emits no
NAME -- the argparse ones -- index as placeholders:

    hee-exif (1)      - hee-exif command
    hee-fields (1)    - hee-fields command

Searchable, but not discoverable: `man -k exif` will not say what it does. Per
rule 17 the fix belongs in each tool's own help text, not in the generator.

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
