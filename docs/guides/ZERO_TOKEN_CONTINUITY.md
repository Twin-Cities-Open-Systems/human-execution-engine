# Zero-Token Continuity Plan

Real runbook for Spencer to keep working when a Claude session isn't
available -- weekly usage cap hit, no session to spawn, or just a
deliberate break from spending tokens. Everything below is a plain
local command: no LLM call, no agent, nothing that costs anything.

Real trigger (2026-08-24): "will need a plan for continue work with 0
token work only if weekly limit reached" -- asked while at 87% of
weekly usage mid-session. Several tools already in this repo
(`hee-ticket`, `hee-publish`, `hee-worktree`, `hee-git-merge`) were
built specifically to do real mechanical work without an LLM call;
this doc is the explicit "what do I run when Claude itself isn't
there" checklist that ties them together, not a new tools list.

## Works with zero Claude tokens, right now

**Review and merge open PRs** -- the actual review judgment is yours;
the tool is a plain Python script, no LLM involved:

```
hee git-merge --action approve   # y/N/s/e/c per PR, real gh pr review calls
hee git-merge --action merge     # same loop, real gh pr merge calls
hee git-merge --action batch     # picks a dependency-complete batch, tracks it as a hee-ticket
hee git-merge --action optimize  # real agent/parallelism estimate off ready PRs
```

**Keep every cloned repo in sync**:

```
make -f tooling/bootstrap.mk health-all-repos    # status only, no writes
make -f tooling/bootstrap.mk pull-all-repos      # fast-forward only, skips real dirty repos
make -f tooling/bootstrap.mk refresh-all-repos   # both
make -f tooling/bootstrap.mk clone-all-repos     # pick up any new org repo
```

**Secrets** -- sealing/using credentials never needed Claude in the
first place:

```
hee-cred -seal <account> -recipients "<gpg-id>"
hee-cred -pass <account> -exec -- <cmd>
```

**Log new work without filing a GitHub issue** -- capture it locally so
nothing gets lost, file the real issue once a session's back if it
needs real writeup/judgment:

```
hee-ticket -new "<title>"
hee-ticket -list
hee-ticket -advance <id>   # idea -> footgun -> dogfood, one step at a time
```

(A `-close` with comma/range/regex selection is real but still sitting
in an unmerged PR as of this writing -- check `hee-ticket -list` first
if these three don't match what's actually installed.)

**Real activity/status reporting** -- `hee-publish` pulls the GitHub
Events API directly, no LLM call. Real but still sitting in an
unmerged PR as of this writing -- confirm it's actually installed
(`hee list` should show it) before relying on it:

```
hee-publish
```

**Mechanical GitHub ops** -- anything that's a direct, unambiguous
action (not a judgment call) is just `gh`:

```
gh pr list --author touchy-claude --state open
gh pr view <n> --repo <org>/<repo>
gh pr comment <n> --repo <org>/<repo> --body "..."
gh issue close <n> --repo <org>/<repo>
gh api rate_limit --jq '.resources'
```

**Per-session worktrees** -- if a fresh Claude session does become
available mid-cap (a different weekly window, a different account),
give it its own working directory instead of colliding with whatever's
checked out:

```
hee-worktree start <branch> [--from <base>]
hee-worktree list
hee-worktree done <branch>
```

## Needs real judgment -- queue it, don't force it

Don't try to hand-roll these without Claude; log them with `hee-ticket
-new` instead so they're ready the moment a session's back:

- Novel bug diagnosis / root-cause work on something not already
  understood
- Doctrine/policy writing that needs real synthesis, not a template fill
- Code review judgment calls beyond "does CI pass" (a human `y/N` on
  `hee git-merge` is fine -- writing *new* review comments that need
  real reasoning about the diff is not a 0-token task)
- Anything that needs cross-referencing multiple repos/systems to make
  a decision, not just to run a command

## Resuming once a session's back

A fresh session's first real move should be a `git fetch`/`pull` sweep
across the repos touched during the gap, plus `hee-ticket -list`
wherever local tickets picked up new work -- that queue is the actual
record of what happened while no session was running, not chat
scrollback that isn't there anymore.
