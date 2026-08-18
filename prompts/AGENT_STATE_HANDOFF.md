# prompts/AGENT_STATE_HANDOFF.md

Companion to [`prompts/INIT.md`](INIT.md) — that's the entry, this is what to
do at `shift_close` (`blueprints/shift-init-v1.yaml`) so the *next* agent's
`history_recap` has something real to read.

## What to actually do at shift_close

1. Follow `shift_ticket_lifecycle` (`contracts/shift-schedule-v1.contract.yaml`)
   steps 4-7: execute in `docs/guides/GIT_GH_WORKFLOW.md` order, using
   `scripts/hee_git_ops.sh --act` for every mutation (see `INIT.md` §4 —
   `HEE_TOOL_MODE=ACT` required, `BLOCKER` if it isn't set), verify the work,
   close the shift ticket, report to oper.
2. If this shift produced anything worth a pill (a real decision, a real
   incident, a real state change) — add it under
   `docs/history/state_capsules/` or `docs/history/status_capsules/`,
   dated, per the existing formats there. Not every shift needs one; don't
   pad it if nothing's actually pill-worthy.
3. Regenerate the index: `python3 tools/hee-pill-index.py --write`. This is
   how the pill you just wrote (if you wrote one) actually becomes visible
   to the *next* shift's `history_recap` — it reads
   `docs/history/PILL_INDEX.md`, not the raw capsule directories directly.
4. Record the metrics `contracts/shift-metrics-v1.contract.yaml` requires:
   `shift_open_at`, `shift_close_at`, `touched_refs` at minimum. State
   explicitly what couldn't be captured rather than omitting it silently —
   never fabricate a value.

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
- Do not claim a pill was written if it wasn't, and do not claim the index
  was regenerated if the command wasn't actually run.
