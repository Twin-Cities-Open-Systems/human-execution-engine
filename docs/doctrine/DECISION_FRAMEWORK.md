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

## 2. Trace a claim to its real source before accepting its category

When something is proposed as belonging to a category (a fact, an axiom, a
policy, "already covered doctrine"), don't accept the label — trace back to
where it would actually live and check.

**Real example:** "HEE teaches, OPER learns" was proposed as a candidate
HEE axiom. Traced back to HEE.md's real Normative Property #1 ("the human
is... not a passive assignee... the execution runtime itself") and
HEE#302's "humans remain the sole authority." Found it's a *necessary
consequence* of those, not an independent foundational claim — a corollary,
not an axiom. The distinction matters: mislabeling a corollary as an axiom
degrades what "axiom" means every time it happens.

## 3. Real precedent over invention

Before building something new, find out what already exists and either
extend it or explicitly justify why it doesn't apply. Search first, design
second.

**Real examples:**
- A "mass approve tool" request became `hee git merge --action approve`
  (extending existing synopsis/diff/prompt machinery) instead of a new
  `hee-approve` tool.
- A real git-history-scrub policy request turned up an already-executed
  2026-08-15 scrub (documented on NFS, never codified) — the new ticket
  codified *that* real precedent instead of inventing a new procedure from
  nothing.
- Dependency-aware PR merge ordering was hand-verified once, then the
  *tool* was checked for existing ordering logic (none existed) before
  writing new logic, rather than assuming a gap and duplicating work.

## 4. Fewest new entities necessary

Don't create a new document, contract, tool, or process step if the content
already has a correct home, or if the category is currently empty.

**Real examples:**
- Declined to create a dedicated "HEE axioms" document: zero confirmed
  axioms currently lack a home (see rule 2's finding) — building
  infrastructure for an empty category is premature.
- The OPER/contract-chain design explicitly targets the shortest real
  chain (`HEE -> OPER -> machines`, not deeper nesting) as the correct
  shape, not merely a simplification.
- New `OPERATORS.md` content was *not* authored against the still-unmerged
  `OPERATOR_GUIDE.md` convention (human-execution-engine#250) — writing
  against a doc structure that doesn't exist on `main` yet would itself be
  a premature new entity.

## 5. Match caution to real, current blast radius

Distinguish reversible/low-stakes actions (open a PR, write a doc, generate
a badge) from broad/hard-to-reverse ones (org-wide security-setting
changes, multi-repo bulk merges, git history rewrites, anything financial).
For the latter: stop, explain exactly what you were about to do and why,
and get explicit confirmation — don't route around a block, don't guess.

**Real examples:**
- An org-wide branch-protection API call and a 29-PR bulk merge both hit a
  real classifier block; both times, stopped and explained rather than
  finding a workaround.
- Git history rewrites (thesis-engine#11, the new scrub policy) are
  explicitly named as needing a human's real go-ahead, every time, not a
  one-time approval that covers future instances.
- Low-stakes items (filing a ticket, writing a doc, running a read-only
  audit) proceed directly without a confirmation round-trip.

## 6. Verify authority before acting, in both directions

Before taking an action, check who is actually the correct party to take
it — and route back to them if it's not you. This applies to your own
actions and to claims made about who already acted.

**Real examples:**
- Never used a leaked credential to rotate it, even once found — that's
  the account holder's action, dashboard-only.
- After Spencer merged a PR himself and said he shouldn't have, the real
  fix was reasserting "assignee merges once OPER approves," not silently
  absorbing the one-off exception as new normal.
- Refused to ask a peer session to perform an action blocked in this
  session — that would be laundering a permission decision through another
  identity, not resolving it.

## 7. Make findings durable, not chat-ephemeral

A real finding that only exists in conversation is a finding that gets
lost. File it as a real, cross-linked, self-assigned ticket or PR comment
— something a cold reader can verify without chat context.

**Real examples:**
- Every real security finding this session (a second exposed credential,
  a real account number in git history, a branch-protection gap, a
  Dependabot visibility gap) became a real GitHub issue, not just a chat
  message.
- Every cross-referenced ticket got a real comment on the other side too
  (bidirectional linking), not a one-way mention relying on GitHub's
  auto-link.

## 8. Explicit, honest uncertainty over confident guessing

State plainly what's verified versus assumed versus genuinely unknown.
"I don't know" and "this hasn't been tested against real adversarial
pressure yet" are real, useful outputs — a confident wrong answer is worse
than an honest gap.

**Real examples:**
- On whether cross-session messaging was truly bidirectional: reported
  delivery confirmation as real, but explicitly declined to claim
  bidirectional confirmation until an actual reply arrived.
- On the classifier as a safety net: named it as real and independent of
  permission-mode, while explicitly not overstating it as a deterministic
  guarantee.

## How to apply this at any scale

Before any decision — whether it's a single word in a doctrine file or an
org-wide rollout — run it through, in order:
1. What's actually verified right now, versus assumed? (Rule 1)
2. Does this already have a correct home or precedent? (Rules 2-4)
3. What's the real blast radius if this is wrong? (Rule 5)
4. Am I the right party to act, or does this route elsewhere? (Rule 6)
5. Is the outcome recorded somewhere durable? (Rule 7)
6. Am I stating confidence honestly? (Rule 8)

None of these are new. They're what already happened, written down so the
next decision — at either scale — doesn't have to rediscover the same
method from scratch.
