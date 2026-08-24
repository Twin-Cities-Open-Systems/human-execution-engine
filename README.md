# Human Execution Engine (HEE)

[![CI/CD Pipeline](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/actions/workflows/ci.yaml/badge.svg)](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/actions/workflows/ci.yaml)

HEE is a **doctrine-first execution framework** for coordinating human reasoning, machine assistance, and automation **without ambiguity**.

It prioritizes:

- correctness over consensus,
- structure over vibes,
- determinism over convenience.

This repository is the **canonical source of HEE doctrine**.

---

## Continuity: what happens when Claude runs out of budget

Real constraint, not hypothetical (hit 2026-08-24: ~90%+ of weekly Anthropic
usage on the primary working session). Fallback tiers, honestly marked --
**proven** (used for real tonight), **designed, untested**, or **not yet
built**:

1. **Another Claude session/peer picks up the work -- proven.**
   [`prompts/INIT.md`](prompts/INIT.md) is the canonical bootstrap entry
   point: point any Claude session at it and it re-derives full context
   (shift-init ceremony, pill index, governing contracts). Used live
   tonight across 3 concurrent sessions. **Real limit**: usage budget is
   almost certainly shared at the account/subscription level, not
   per-session -- this tier buys parallelism, not more total budget.
2. **A local model for narrow binary-predicate gates -- designed, not yet
   built.** [`hee/docs/local-llm-architecture.md`](hee/docs/local-llm-architecture.md)
   (thesis) + [HEE#352](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/issues/352)
   (tracking issue). Scope is deliberately narrow: a sub-4B quantized model
   answering a yes/no gate in <100ms, *not* a Claude replacement for real
   reasoning/agentic work. Real infra check 2026-08-24: PVE host has 8
   LXCs running and ~15GB RAM free -- capacity exists, nothing deployed
   yet. No `ollama`/`llama.cpp`/equivalent installed anywhere in the fleet
   as of this writing.
3. **A different vendor's agentic coding CLI as a full drop-in -- designed
   in theory, never actually tested.** `INIT.md`'s doctrine-first design is
   meant to be model-agnostic ("point any agent, from anywhere, at this
   file"), but this has only ever been exercised by Claude sessions. No
   non-Claude agentic CLI (Gemini CLI, Aider, Cursor Agent, etc.) is
   installed anywhere in the fleet, and the claim that a different model
   could actually pick up HEE work cold has **not been verified**. Real
   gap, not yet closed -- don't assume this tier works until it's actually
   been run once.
4. **A second Anthropic account/API key for urgent-only work -- available,
   not automated.** Bridges the narrowest, most time-sensitive items only;
   real cost/ops tradeoff (separate billing), not a scale solution.

Tiers 2 and 3 are the real, open work: HEE#352 covers tier 2's build; tier
3 has no tracking issue yet and needs one before it's more than an idea.

---

## Tooling & Workflows

- Patching workflow: `docs/tools/patching.md`
- Operator tools: `tools/oper/README.md`
- Automation tools: `tools/auto/README.md`

## Tooling docs

- Patching workflow: `docs/tools/patching.md`

## Core Principles

- **Doctrine defines correctness.**
- **Operations enforce doctrine.**
- **Instances execute within doctrine.**

Doctrine is **standing, non-terminal**, and validated **strictly**.

---

## Repository Layout

### `blueprints/`

Authoritative doctrine.
This directory defines:

- world-derived core tools,
- blueprint and plan schemas,
- validator contracts,
- chat header structure,
- the HEE doctrine index.

Nothing here is operational.

> **Rule:** Doctrine MUST validate in strict mode.

### `docs/`

Narrative documentation only:

- explanations,
- rationale,
- examples,
- RFCs.

RFC-style identifiers are **reserved exclusively** for `docs/rfc/`.
RFCs may reference doctrine identities but MUST NOT define them.

### Operational directories (e.g. `ci/`, `ops/`, scripts)

Automation and enforcement that **consume doctrine**.
These are implementation details, not sources of truth.

### `tools/`

Operator tools and utilities that support HEE execution.
Includes the `apply-var-patch` tool for applying patches from VAR environment variables.

---

## Doctrine Rules (Non-Negotiable)

- Doctrine files:
  - MUST have `result: false`
  - MUST validate in **strict** mode
  - MUST use deterministic identity (`seed` + derived `id`)
- YAML:
  - MUST NOT be hand-edited once tooling exists
  - MUST be formatted canonically
  - MUST NOT contain embedded shell scripts
- Changes:
  - Prefer **raw GitHub links** over copy/paste when reviewing or merging
  - Minimize diffs
  - Increment `schema-version` only when meaning changes

---

## Validation & CI/CD

CI/CD enforces:

- strict doctrine validation,
- schema correctness,
- formatting invariants.

Future lanes include:

- multi-language “Hello World” compile tests,
- metrics export compatibility (Prometheus + SNMP),
- doctrine-driven MIB generation.

---

## What HEE Is Not

- Not a workflow tool
- Not a prompt library
- Not an agent framework
- Not opinionated about implementation language

HEE defines **what must be true**, not **how you make it true**.

---

## Why HEE

Modern development fails less from lack of talent and more from ambiguity:
unclear authority, drifting scope, unverifiable claims, and
“works on my machine” reasoning that collapses under handoffs.

HEE exists to make work **correct by construction**.

It does this by:

- separating **doctrine** from **operations**,
- enforcing **strict validation**,
- requiring **evidence** for terminal actions,
- and using **deterministic identity** so changes remain auditable and merge-safe.

The goal is simple:
turn intent into **verifiable outcomes** without relying on memory, vibes,
or fragile UI state.

---

## Thesis vs. Duople

HEE has two content states, and the difference matters:

- **Thesis** — a claim to be stress-tested. Might be a raw idea, a pasted
  external chat, a proposal, a first draft. Not wrong to have around, but
  not yet trustworthy on its own say-so.
- **Duople** — a claim that's been reduced to its binary-predicate,
  HEE-native form: verifiable, evaluable, evidence-backed. This is what
  "correct by construction" (above) actually looks like once a Thesis
  has done its work.

**Why it matters**: HEE's whole premise is that unverifiable claims are
the failure mode to design against (see "Why HEE" above). A Thesis that
gets treated as settled just because it sounds confident or has been
repeated is exactly the "works on my machine" problem this project
exists to prevent — just in prose form instead of code. Labeling
something Thesis is not a demotion; it's an honest status. It graduates
to Duople on evidence, not on iteration count or how long it's been
argued.

---

## Status

HEE doctrine is **active and evolving**.
History is preserved via:

- git history (authoritative),
- explicit `schema-version`,
- narrative RFCs when needed.

If you are reading this to “get started,” start in `blueprints/`.

## Patching (CBA safe)

- See docs/tools/patching.md

## HEELANG example

HEELANG is a compact, hashable vocabulary used to label high-signal workflow events and artifacts.

Example (tokens from a reconcile session):

- `RECONCILE`
- `PILL-WRAPPER`
- `DRIC-DELTA`
- `EVIDENCE-IS-TRUTH`
- `WROTE`
- `SHA256`
- `BYTES`
- `TERMINATION-POINT`

## Dogfood: this session (docs + lint + workflow lessons)

What we did (high signal):

- Used targeted lint runs to stay focused: `pre-commit run markdownlint-cli2 --files <file...>`
- Verified changes with minimal diffs and kept churn low.
- Fixed markdown issues via safe, deterministic edits.
- Enabled markdownlint autofix in pre-commit to prevent recurring paper-cuts.

Lessons learned:

- **WROTE ≠ CHANGED**: scripts can rewrite a file without changing content; Git only cares about diffs.
- Markdownlint errors like MD012/MD032 are best handled by **autofix**, not hand-editing.
- When autofix is enabled, always **stage + commit the autofix fallout** (or explicitly discard it) to keep the tree clean.

## HEELANG example (dogfood)

HEELANG is a compact, hashable vocabulary used to label high-signal workflow events and artifacts.

Example tokens from a reconcile / triage session:

- `RECONCILE`
- `PILL-WRAPPER`
- `DRIC-DELTA`
- `EVIDENCE-IS-TRUTH`
- `WROTE`
- `SHA256`
- `BYTES`
- `TERMINATION-POINT`

A deal has been reached to sell HEE.
