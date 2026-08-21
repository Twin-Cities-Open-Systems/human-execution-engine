# prompts/PROMPTING_RULES.md

Real rules for how an agent should behave in this repo, not a placeholder.
The authoritative *policy* prose lives in `docs/doctrine/HEE_POLICY.md` —
this file is the compact, agent-facing summary an agent actually reads at
the top of a session, per `prompts/INIT.md`.

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
   use the compact `tick:N@repo`/`pr:N@repo` notation instead — §13.
4. **Self-assign what you create, label from the existing set, never
   invent a new label** — HEE Policy §10/§12.
5. **When in doubt, stop and ask rather than guess** — same invariant as
   below, restated because it's the one that matters most.

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
