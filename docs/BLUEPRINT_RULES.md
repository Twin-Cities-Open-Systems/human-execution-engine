# Blueprint doctrine rules

This document governs changes to files in `blueprints/`.

These files are **authoritative doctrine**.
Changes must be deliberate and minimal.

---

## General Rules

- Doctrine is **non-terminal**.
  - `result` must always remain `false`.
- If meaning changes, increment `schema-version`.
- Prefer minimal diffs.
- Avoid introducing new fields unless necessary.
- Preserve backward compatibility where reasonable.

---

## Change Process

1. Propose the change clearly (what problem it solves).
2. Update the relevant doctrine file.
3. Bump `schema-version` if the schema or constraints change.
4. Run validation (or reason through validator implications).
5. Ensure no circular dependencies are introduced.

---

## Validation Expectations

- All doctrine files must be parseable.
- Declared dependencies must exist and match schema-version.
- Constraints must remain descriptive and evaluatable.
- Unknown keys are allowed temporarily but must be resolved.

---

## Non-Goals

This directory is not the place for:

- prompts,
- agent instructions,
- implementation logic,
- operational plans.

Those belong elsewhere.
