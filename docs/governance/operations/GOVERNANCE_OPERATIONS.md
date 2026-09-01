# GOVERNANCE OPERATIONS (FROZEN / CANONICAL)

**Status:** Frozen and Canonical (Ratified 2026-01-26)
**Authority:** Single Responsible Operator (SRO): Spencer Butler
**Scope:** CI governance rules only (mechanical, enforceable, testable)

## Immutability Notice

This file is **frozen**. Changes are **invalid** unless:

- A change record is added under `docs/governance/operations/changes/`
- `docs/governance/operations/INTEGRITY_SHA256SUMS` is updated
- SRO approval is recorded in the change record

(Collapsed 2026-08-27 from three separate files -- `GOVERNANCE_CHANGE_PROCESS.md`,
`GOVERNANCE_OPERATIONS.md`, `GOVERNANCE_VERSIONING.md` -- into this one, per
[docs/governance/operations/changes/2026-08-27_collapse-three-governance-ops-files.md](changes/2026-08-27_collapse-three-governance-ops-files.md),
approved by Spencer directly. Same process, same scope, same authority
model -- the three files repeated an identical Immutability Notice and
SRO/scope header three times with zero real change records ever filed
since ratification; this is that same content once instead of three times.)

## Purpose

Established normative framework for ongoing operation, evolution, and versioning of CI governance rules.
Defines mechanical processes for governance rule lifecycle management while maintaining strict scope boundaries.

## Authority Model

- **Single Responsible Operator (SRO):** Spencer Butler
- **Model:** Explicit operator sovereignty (no committees / multi-party approval)
- **Scope:** CI governance rules only (mechanical, enforceable, testable)

## Scope Boundaries

Included:

- CI governance rule lifecycle, versioning, enforcement mechanics
- `ci/governance/*` components and CI pipeline integration

Explicitly excluded:

- HEE doctrine evolution, human compliance processes
- Social/organizational governance, violation tracking systems
- Compliance monitoring beyond CI enforcement

## Core Invariants

1. **No Aspirational Governance** — rules cannot require non-existent approval bodies.
2. **Enforcement Binary** — rules either enforce immediately or do not exist.
3. **Reactive Evolution Only** — changes only in response to concrete triggers, never hypothetical.

## Change Process

*(formerly `GOVERNANCE_CHANGE_PROCESS.md`)*

### Evidence-Gated Workflow (Binary)

#### 1) Trigger (Concrete Event)

Example triggers:

- CI false positive/negative
- rule bypass discovered
- missing enforcement for a real violation class

#### 2) Change Record (Required)

Create: `docs/governance/operations/changes/YYYY-MM-DD_<slug>.md`

It MUST include:

- Trigger
- Evidence
- Proposed change
- Enforcement impact (what now fails/passes)
- Version bump (PATCH/MINOR/MAJOR)
- `Approved-by: Spencer Butler`

#### 3) Validation

- Add/adjust tests or fixtures proving the trigger and the fix
- Demonstrate deterministic outcomes

#### 4) Enforcement

- Merge only when enforcement is live and binary
- Update integrity hashes

### Emergency Rollback

- Revert to last known-good commit
- File a change record describing trigger + evidence
- Re-apply via standard workflow

## Versioning Scheme

*(formerly `GOVERNANCE_VERSIONING.md`)*

Governance changes are versioned using **MAJOR.MINOR.PATCH**.

### PATCH

- Bugfixes that do not change pass/fail behavior for compliant repos
- Error message improvements only

### MINOR

- Adds immediately enforced checks
- Backward-compatible tightening (existing compliant repos remain compliant)

### MAJOR

- Breaking enforcement changes (previously compliant repos may fail)
- Renames/moves of canonical governance paths
- Required schema changes that invalidate old state

### Deprecation

No shadow modes.
Any removal/replacement must be explicit via change process + version bump + documented migration.
