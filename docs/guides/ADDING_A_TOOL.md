# Adding a tool, end to end

A followable procedure for someone who has never added a `hee` tool. Every
command below is real and was run in this order to ship `hee quota watch`,
which is used throughout as the worked example.

This is the **walkthrough**. [`MANPAGE_PIPELINE.md`](MANPAGE_PIPELINE.md) is
the **reference** for how a page travels from a tool to `man.tcos.us`,
including a real gap at stage 5. Read this to do the work; read that to
understand the machinery.

## 0. Make sure `hee` actually runs

Do this first. It has bitten a real operator.

    hee list

If that says `hee: command not found`, `~/.local/bin` is on your `PATH` but
empty. `heerc` prepends the directory and **nothing populates it** — tracked
as `human-execution-engine#649`. Until that lands, symlink the tools you need
from `tooling/bin/`, or invoke them by path:

    ~/git/human-execution-engine/tooling/bin/hee-quota status

Every example below uses the short form and assumes `hee list` worked.

## 1. Find the tool this belongs to — do not start by writing one

**This is the step people skip, and it is the one Spencer pushes back on.**
A new top-level `hee-<cmd>` is a last resort, not a starting point.

    hee list

Read the whole list. For the watcher, three candidates looked plausible:

| candidate | what it actually is | verdict |
|---|---|---|
| `hee-check` | repo and policy **gates** | no — this is not a gate |
| `hee-stat` | `stat(1)`'s `-c FORMAT` over namespaced resources | no — different interface entirely |
| `hee-quota` | **"do I have headroom before I start a batch?"** for GitHub API pools, with `status \| warn \| wait` | **yes** |

`hee-quota` already modeled a pool as `remaining/limit` and already answered
the go/no-go question. Host memory *is* an exhaustible pool: you have a
budget, you spend it, and finding out reactively is the failure. Same
question, same answer shape — so this was an extension, not a new tool.

Write down why you rejected the others. That reasoning belongs in the PR.

## 2. Start at the least capable language that does the job

Graduate only when actually outgrown:

    library/bash/*.shfn.bash  →  tooling/bin/* (sh)  →  *.py  →  Go/Rust

Keep the tool thin. Logic that deserves a test goes in `library/`, where it
can have one.

## 3. Write the help text — it *is* the man page

`hee-gen-manpages` does not read a separate document. It runs your tool's own
help and captures the output.

> A tool's help text **is** its man page. Help quality is documentation
> quality, and a tool whose help is broken publishes its breakage.

Measured 2026-08-31: **30 of 37 published pages contained captured run output
instead of documentation**, because those tools ran instead of printing help.
Fix the tool's help and the page fixes itself.

So write the help as the thing a stranger reads, and say *why*, not only
*what*:

    hee-quota watch --pools host   -- sample on an interval and STOP ON ITS
                                      OWN. Bounded by design: --samples
                                      defaults to 180 and there is no
                                      unbounded mode. A watcher that can run
                                      forever is the bug it was built to catch.

## 4. Declare the section

Line 2 of the file, before anything else:

    #!/usr/bin/env python3
    # section: 1

Section 1 is a user command. Without this the generator cannot place the page.

## 5. Prove the old behavior still works

Before generating anything, run the tool the way it was called *yesterday*:

    hee quota status

If that output changed for existing callers, you have not extended a tool —
you have broken one. Grep both repos for callers and list them in the PR.

## 6. Dry run the generator, and read the diff

**Dry run is the default and writes nothing.** This is deliberate — Spencer,
2026-09-01: *"I don't like that it just writes files when you run it without
args."*

    hee gen-manpages

Read what it says it would change. If it reports changes to pages you did not
touch, someone else's work is in your tree; sort that out first.

## 7. Write the pages, then stage only yours

    hee gen-manpages --write
    git add man/tools/hee-quota.1.md man/tools/man1/hee-quota.1
    git checkout -- man/                 # drop everyone else's regenerated pages

The generator has **no per-tool targeting** — it regenerates everything. If a
colleague is editing another tool on another branch, staging everything will
collide with them. Stage your two files and drop the rest.

**Never hand-edit a generated page.** Change the help and regenerate.

## 8. Read your page the way a user will

    man hee-quota

If nothing is found, run `make manpath` in `dotfiles` once — it is per-account
and is a branch of the pipeline, not a step after publishing. A page is
readable from your checkout without ever reaching prod, which is why
`man.tcos.us` can be stale while `man hee-quota` is current.

## 9. Save a real dogfood run as an example

Policy §6: the example goes in `examples/` at the root of **the repo the tool
lives in**, and it is a real run's actual output — never a hand-written
mockup. A mockup that drifts from the tool is worse than no example.

## 10. Land it

Branch, PR, assign, set every field in the same step:

    git checkout -b kiosk/quota-host-pools main
    gh pr create --base main --assignee touchy-claude
    hee fields set --repo Twin-Cities-Open-Systems/human-execution-engine \
      --number NNN --type Feature --priority P2 --effort S

Never commit to `main`. No "Generated with Claude Code" footer and no
`claude.ai/code` link in an issue, PR body, or comment.

## What to expect afterward

Stages 1–4 are automated and reliable. **Stage 5 — content reaching
`man.tcos.us` — is manual and partly undefined**, and is written down as a
`CRITICAL` gap rather than papered over. Your page being correct locally does
not mean it is published. See
[`MANPAGE_PIPELINE.md`](MANPAGE_PIPELINE.md#5-reaching-prod----the-gap).

## The one-screen version

    hee list                      # 1. find the tool this belongs to
    $EDITOR tooling/bin/hee-foo   # 2-4. extend it; help text IS the page
    hee quota status              # 5. prove old behavior is unchanged
    hee gen-manpages              # 6. dry run, read the diff
    hee gen-manpages --write      # 7. then stage ONLY your two pages
    man hee-foo                   # 8. read it as a user
    hee check all .               # gate before you push
