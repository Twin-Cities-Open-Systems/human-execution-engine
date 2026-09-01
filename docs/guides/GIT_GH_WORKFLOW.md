# Git/GitHub Workflow (HEE)

## Objective

Keep `main` protected and every change reviewable — without a wrapper
script standing between an agent and ordinary git.

<!-- hee-check:refs-off  both scripts named below were removed by that supersession -->
**Superseded 2026-08-31.** `scripts/hee_git_ops.sh`, its CI presence
check `scripts/hee_ci_gitops_enforce.sh`, and the `HEE_TOOL_MODE`
environment variable are **retired**. <!-- hee-check:refs-on --> The reasoning is recorded below so
this is not relitigated from memory.

## Non-negotiables

1. **Never commit or push directly to `main`.** All work happens on a
   branch and lands through a PR.
2. **Branch protection on `main` is the real control** — it is
   server-side, so it binds every operator, agent, machine and script
   equally, and cannot be bypassed by simply not calling a wrapper.
3. **PRs merge when checks pass and the assignee is satisfied.** A PR
   carrying the `human` label requires explicit human approval before
   merge. No other PR does.
4. **Reference issues and PRs by full URL** — see
   `prompts/PROMPTING_RULES.md` rule 3.

Ordinary `git` and `gh` commands are fine on a branch. Read-only git has
never needed a gate and does not have one.

## Why the wrapper was retired

Real findings, 2026-08-31, from reading all 259 lines of the script and
its CI enforcement:

- **`--reason` was theatre.** It was required on *every* operation,
  including read-only `status` and `log`, and blocked without it — then
  the value was **never used again**. Not logged, not written anywhere,
  not attached to the commit. The in-script comment claimed it existed
  to "force intentionality in agent logs." There was no log.
- **The double gate was not two factors.** `--act` and
  `HEE_TOOL_MODE=ACT` were both supplied by the same agent in the same
  command. Two locks, one key, one hand.
- **The op set could not do the work.** It offered `add`, `commit`,
  `push`, `checkout`, `branch-create`, `tag-create`, `pr-create` — and
  no `merge`, `pr-merge`, `issue-create`, `label`, `pr-edit`, `pull`,
  `fetch`, or `rebase`. Most real work had no sanctioned path, so the
  agent had to either stall or break the rule.
- **The governance contradicted itself.** Rule 1 banned `gh` mutations
  by agents; rule 12 instructed agents to run `gh issue create`. There
  was no `issue-create` op.
- **It had already lost two fights with reality.** `checkout` and
  `branch-create` carry in-script comments explaining they had to be
  *exempted* from the gate because it made them impossible to use for
  their own purpose (2026-08-18, first real use).
- **CI "enforcement" enforced its own existence.**
  `hee_ci_gitops_enforce.sh` checked that the script existed, that docs
  mentioned it, and that CI called the checker — nothing about whether
  any mutation actually used it. It ran with `continue-on-error: true`,
  so it could not fail a build.
- **It was never followed.** `prompts/INIT.md` recorded this in its own
  text: *"Known gap … this hasn't actually been followed in practice
  yet -- said here so it stops being silently true."*

The legitimate goal — *don't let an agent silently push to `main`* — is
kept, and moved to branch protection where it actually binds.

## Standard workflow

```bash
git switch -c feature/short-description       # or <host-or-session-id>/… — see HEE_POLICY §2
# make changes
git add <paths...>
git commit -m "type(scope): concise imperative description"
git push -u origin HEAD
gh pr create --base main --title "…" --body "…"
```

Branch prefixes and their post-merge handling (`feature/` deleted,
identity-prefixed kept as an audit trail) are unchanged — see
`docs/doctrine/HEE_POLICY.md` §2.

## Definition: mutating operations

Any command that changes repo state, commit graph, tags, branches,
remotes, or GitHub artifacts — `git commit`, `git merge`, `git rebase`,
`git push`, `git tag`, `gh pr create`, `gh pr merge`, `gh repo create`.
None of these require a wrapper. All of them are still forbidden
directly against `main`.

## Merging

Merge via `gh pr merge --squash`, or `hee-git-merge` where it is already
in use. Add `--delete-branch` only for `feature/`-prefixed branches;
identity-prefixed branches are kept post-merge by design.
