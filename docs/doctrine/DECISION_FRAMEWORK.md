# HEE Decision Framework

## Purpose

This document formalizes the real decision-making logic actually used, not
a theoretical model written in advance of practice. Every rule below is
extracted from genuine decisions made during a single real session
(2026-08-22/23, touchy-claude, org-wide security/tooling/governance work),
with the real example that produced it. Trigger: Spencer's direct ask,
"formalize the logic and methods you have used this session to make
decisions based on current poli[c]y. we need a framework that is documented
so we can have greater fine grain control over the org at large (and tiny)."

Fine-grain by design: every rule here applies identically to a single word
in a doctrine file and to a 15-repo security rollout. Scale changes the
blast radius, not the method.

---

## 1. Verify, never trust a self-report

Never accept a claim — your own tool's echo, another agent's status line,
a prior session's assertion, a stale doc's "EXECUTED CHANGES" note — as the
real state. Independently re-check against the actual source.

**Real examples:**
- A branch-protection enable loop reported 15/15 success; independently
  re-checked via `gh api .../vulnerability-alerts` (GET, not the same PUT
  call) before trusting it.
- `reviewDecision: APPROVED` looked sufficient; checked `dismiss_stale_reviews`
  on the two repos with pre-existing protection and found it was `false` on
  both — a real gap the "APPROVED" label alone hid.
- A 2026-01 structure-compliance audit (cited in HEE#301) claimed specific
  files were moved; verified false against the live tree seven months
  later. Treat any "already done" claim as a hypothesis to check, not a fact
  to relay.
- Two real, independent collisions the same night (2026-08-24) both
  traced back to acting on stale/assumed state instead of a fresh check:
  `hee-name` allocated the identical name `kenny` to two concurrent
  sessions ([HEE#336](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/issues/336));
  a shared git working directory let one session's `checkout` silently
  yank another session off its own branch mid-task. Neither would have
  happened if the acting session had freshly verified shared state
  immediately before acting, rather than trusting what it last knew.

**Why this is the actual mechanism, not just caution, per Spencer
directly (2026-08-24)**: "when you verify before acting you enforce a no
collision system by default." A verification check (`git fetch`, `gh api
... reviewDecision`, re-reading a file) has near-zero marginal cost; what
it prevents — a collision, a bad merge, hours untangling stale state —
has no ceiling. Same structural shape as the `left(capex)` thesis
(`theses/btc-energy-time-spread.md`'s "cheap input relative to value
produced = structural spread," extended past markets): cheap check now,
unbounded avoided cost later. The asymmetry only holds while the check
itself stays cheap — a real check should be a 0-token/deterministic
operation (a `git status`, a `gh api` call), not an LLM call, or the
"verification is nearly free" premise stops being true. See
[fleet-ops#208](https://github.com/Twin-Cities-Open-Systems/fleet-ops/issues/208)
for the tracked discipline of keeping checks on the cheap side of that
line.
: DECISION_FRAMEWORK.md -- formalize this session's real logic)
## How to apply this at any scale

Before any decision — whether it's a single word in a doctrine file or an
org-wide rollout — run it through, in order:
1. What's actually verified right now, versus assumed? (Rule 1)
2. Does this already have a correct home or precedent? (Rules 2-4)
3. What's the real blast radius if this is wrong? (Rule 5)
4. Am I the right party to act, or does this route elsewhere? (Rule 6)
5. Is the outcome recorded somewhere durable? (Rule 7)
6. Am I stating confidence honestly? (Rule 8)
7. Is this constructed correctly before I run it, not after? (Rule 9)

None of these are new. They're what already happened, written down so the
next decision — at either scale — doesn't have to rediscover the same
method from scratch.
