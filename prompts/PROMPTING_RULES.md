# prompts/PROMPTING_RULES.md

Real rules for how an agent should behave in this repo, not a placeholder.
The authoritative *policy* prose lives in `docs/doctrine/HEE_POLICY.md` —
this file is the compact, agent-facing summary an agent actually reads at
the top of a session, per `prompts/INIT.md`.

**This file is org-wide canonical, not just for this repo** — every other
TCOS repo's `CLAUDE.md` pulls it in via `@~/git/human-execution-engine/prompts/PROMPTING_RULES.md`.
That import is a **real, required assumption that every repo is checked
out under `~/git/<repo>`** (this org's own convention, per `bin/init-org.sh`'s
`WORKSPACE_DIR="${HOME}/git"`) — `~` is the most portable path form
Claude Code's `@import` actually supports (confirmed: no `$HOME`/env-var
expansion, no workspace-relative mechanism). On a machine that doesn't
follow that layout, the import silently fails to resolve and this file
won't be in context for other repos' sessions — if you're not sure it
loaded, read this file directly rather than assume it did.

## The rules

1. **Every git/gh mutation goes through the wrapper.** Raw `git commit`,
   `git push`, `gh pr create`, etc. by an agent are not allowed — use
   `scripts/hee_git_ops.sh <op> --act --reason "..."` with
   `HEE_TOOL_MODE=ACT` set. If asked to mutate without that mode set:
   `BLOCKER: Mutation requested but HEE_TOOL_MODE!=ACT or --act missing. Refusing.`
   — then stop. Read-only git (`status`/`diff`/`log`/`show`) is fine
   directly. See `docs/guides/GIT_GH_WORKFLOW.md` for the full spec.
2. **Never fabricate.** No invented file references, no claimed-but-unrun
   commands, no asserted "landed"/"merged"/"done" without checking the
   actual state first. Includes the subtler form: never redirect stderr
   to `/dev/null` (or otherwise discard an exit code) and then interpret
   the resulting silence as a real negative result — check *why* a
   command produced no output before reporting what that silence means
   — HEE Policy §6.
3. **Real links, not bare shorthand**, for issue/PR references — HEE
   Policy §5. Structured work files (contracts/blueprints/doctrine YAML)
   use the compact `issue:N@repo`/`pr:N@repo` notation instead — §13.
4. **Self-assign what you create, label from the existing set, never
   invent a new label. Only the opener closes/merges their own ticket
   or PR** — explicit exception only, never inferred — **HEE Policy
   §10/§12.**
5. **When in doubt, stop and ask rather than guess** — same invariant as
   below, restated because it's the one that matters most.
6. **Target GNU tool syntax/behavior by default**, not BSD or another
   implementation — real, not stylistic (`sed -i` requires an explicit
   suffix argument on BSD, optional on GNU; `date -d` is GNU-only) —
   HEE Policy's GNU Tools Preference Policy.
7. **When a doc's stated design contradicts real precedent already in
   use, surface both sides and reconcile — don't silently pick one.**
   Review why the old standard existed and why current practice
   diverged, reason toward the best of both rather than a unilateral
   pick, let the human decide on a genuine tradeoff, then canonize the
   resolution back into the doc with its reasoning kept — HEE Policy
   §19.

8. **Commit format and merge flow.** Conventional Commits
   (`type(scope): concise imperative description`; `feat`/`fix`/`chore`/`docs`)
   for every commit and PR title. Merge via `gh pr merge --squash`; add
   `--delete-branch` only for `feature/`-prefixed branches -- `touchy/`-prefixed
   branches are kept post-merge as an audit trail by design (see HEE Policy
   §2). Absorbed from the org's old `WORKFLOW.md`, 2026-08-27.
9. **Issue hierarchy.** Epic (org roadmap, multi-repo, spans quarters) ->
   Feature (one discrete capability) -> Sub-issue (PR-bound tactical work,
   keeps its own labels -- labels don't inherit from the parent).
10. **Three real footguns, absorbed from the org's old
   `ORGANIZATION_BOOTSTRAP.md`, 2026-08-27:**
   - Never run a destructive git clean (`git clean -fdx`, `git reset --hard`)
     immediately after a `git stash pop` in a multi-repo/headless script --
     the just-popped changes sit uncommitted and get purged as noise. Use
     `pull --rebase` or an isolated branch instead of a trailing reset.
   - Any pre-commit hook that runs `git diff`/`git status` internally needs
     a recursion guard (`TCOS_HOOK_RUNNING` env var, checked and set at the
     top, `exit 0` if already set) -- without it, the hook re-triggers
     itself until the shell hits its subshell-depth limit and crashes.
   - Never hardcode a real user's home path (`/home/spencer/...`) into a
     shared init/bootstrap script or template -- use `$HOME` so it works on
     any machine, user, or automated node.
11. **Color/status output goes through the Claude Code `dataviz` skill's
    rules, always -- never bare red/green.** Real trigger, 2026-08-28: an
    agent session built a plain ✅/❌ status table (and had been echoing
    hee-view's 🔴/🟡/🟢 dots uncritically all session) before ever loading
    the skill. Spencer, direct: "this red is anti spencer." Status colors
    (good/warning/serious/critical) ship with an icon + label, never color
    alone, and any real palette gets run through the skill's
    `scripts/validate_palette.js` before shipping -- see `UI_UX_REVIEW.md`/
    `STATUS_AND_PRIORITIES.md` in `thesis-engine` for prior real findings
    from the same validator. Applies org-wide, not just chart code: plain
    chat/table output using red/green as the only distinguishing cue is
    the same failure mode.

## Authority Invariants

- Authority is scoped to this repository and this workflow context.
- No external side effects without explicit operator action.
- When in doubt: stop; do not guess.

## Scope Invariants

- Scope is limited to this repository and this workflow context.
- No external side effects without explicit operator action.
- When in doubt: stop; do not guess.

## Invariants

- Do not violate repository invariants.
