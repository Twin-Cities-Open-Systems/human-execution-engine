# Directory tree cleanup — plan, not yet executed

**Status: plan.** Real ask, 2026-08-21: "it is super hard to find shit."
Dogfooding our own tools while surveying, small bits at a time, not a
big-bang reorg — this doc is the first real snapshot the plan gets
built from, not a finished proposal to just execute.

## Real survey, top level (24 directories)

| Directory | Files | Note |
|---|---|---|
| `docs/` | 104 | By far the largest — real candidate for its own sub-cleanup pass, not solved by this doc |
| `tooling/` | 35 | `bin/githooks/templates/ci/smart-approval` |
| `library/` | 34 | |
| `blueprints/` | 25 | |
| `tools/` | 25 | **Real overlap with `tooling/`** — two top-level dirs with adjacent names and no doc explaining the split |
| `scripts/` | 23 | |
| `ci/` | 14 | |
| `src/` | 13 | |
| `schemas/` | 9 | |
| `extras/` | 9 | Explicitly self-disclaimed: `OPTIONAL / NON-CANONICAL / LOCAL-ONLY`, real observability dashboard inside it, stale since 2026-02-02 |
| `cmd/` | 2 | |
| `workloads/` | 2 | `hello-world/` demo stub |
| `plans/` | 4 (mostly `.gitkeep`) | Real designed structure (`active/archive/doctrine_candidates`), currently empty of real plans |
| `rfcs/` | 4 | |
| `reports/` | 1 | Single file (`wsl-explorer-unc.md`) as its own top-level dir |
| `math/` | 1 | Just a README — placeholder, no real content |
| `man/` | 1 | Legitimate real Unix convention even at 1 file — not flagged as a problem |
| `completions/` | 1 | Same — real convention, shell completions get their own dir regardless of count |
| `hee/` | (15 real subdirs) | `policy/measure/contracts/registries/skills/cards/rrd/gcic/experiments/library/evidence/governance/procedures/docs/tools` |
| `.hee/` | (3 subdirs) | `notes/`, `spool/`, `evidence/` — **real overlap with `hee/`**, different purpose (looks like session/working-state, not doctrine) but no doc says so |

## Real overlaps found, not yet resolved

1. **`tools/` vs `tooling/`** — both real, both populated (25 vs 35
   files), no doc anywhere explaining why two top-level dirs exist for
   what sounds like the same concept. Needs Spencer's real answer
   (same as `claude-touchy`/`touchy-claude`: deliberate breadcrumb, or
   genuine drift to fix) before touching either.
2. **`hee/` vs `.hee/`** — `hee/` is clearly doctrine/governance (15
   real subdirs: policy, contracts, registries, cards...); `.hee/` is
   much smaller and looks like working state (`notes/`, `spool/`,
   `evidence/`) — plausibly a legitimate split (canonical vs.
   session-local), but nothing documents that distinction explicitly.
3. **`math/` and `reports/`** — near-empty (1 file each), real
   candidates for either real content eventually, folding into
   `docs/`, or removal if genuinely dead. `math/README.md` in
   particular has no real content behind it at all.

## Proposed approach — small bits, not one pass

1. **First real bit**: ask Spencer directly about `tools/` vs
   `tooling/` and `hee/` vs `.hee/` — the two real, load-bearing
   overlaps, not the small stragglers. Same canonization discipline as
   every other real drift found this session (HEE Policy §14):
   surface, don't guess, resolve, write the reasoning back.
2. **Second real bit**: a real `docs/` sub-survey — 104 files is too
   large to characterize in this pass; needs its own real inventory
   before proposing anything there.
3. **Ongoing**: as each real bit gets resolved, this doc (or its
   real successor) gets updated with what moved/merged/stayed and why
   — canonized, not silently applied.

## Not done here

No files moved, no directories merged, no decisions made unilaterally
— this is the survey and the proposed order of small steps, per "make
plan and do small bits at a time."
