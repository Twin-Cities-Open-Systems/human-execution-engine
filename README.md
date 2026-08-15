# Human Execution Engine (HEE)

[![CI/CD Pipeline](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/actions/workflows/ci.yaml/badge.svg)](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

HEE is a **doctrine-first execution framework** for coordinating human reasoning, machine assistance, and automation **without ambiguity**.

It prioritizes:

- correctness over consensus,
- structure over vibes,
- determinism over convenience.

This repository is the **canonical source of HEE doctrine**.

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
