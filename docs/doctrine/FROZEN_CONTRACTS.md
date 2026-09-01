# FROZEN_CONTRACTS.md

## Authority

This document records **frozen operational contracts** of the Human Execution Engine (HEE).

These contracts are **non-negotiable invariants**.
They MAY NOT be changed without:

- an explicit PLAN
- disk evidence
- successful verification

Absence of this document previously did NOT imply absence of these contracts.
This document makes them explicit.

---

## PRECHECK — REQUIRED CONTEXT ON DISK

Before accepting this document as authoritative, the following MUST exist:

- ci/governance/check.sh
- hee/governance/fixtures/
- docs/doctrine/
- .github/workflows/ (CI present)

If these paths do not exist, this document MUST NOT be treated as active doctrine.

---

## HARD-FROZEN CONTRACTS

### 1. AGENT EXECUTION MODE (TEXT-ONLY)

- AGENT execution directives MUST be written in plain TEXT.
- Markdown, formatting, or structural markup is FORBIDDEN in execution directives.
- AGENT execution directives:
  - do not allow scope negotiation
  - require disk evidence as output

This rule applies ONLY to execution.
Planning and discussion MAY use other formats.

(Removed 2026-08-27: this rule originally also said execution directives
"do not allow questions," and a separate NO-QUESTIONS EXECUTION RULE stood
here as its own numbered contract. Both directly contradicted the live,
current `prompts/PROMPTING_RULES.md` rule 5 -- "When in doubt, stop and ask
rather than guess" -- which is how the fleet actually operates. Resolved in
favor of the live rule per the Canonization Policy, not silently dropped:
stop-and-ask wins, this file's no-questions language was the stale side.)

---

### 2. WHITELIST PARSER INVARIANT

- Governance output parsing is **whitelist-only**.
- Only known, canonical violation formats are considered real violations.
- All other output is treated as noise by default.

Noise includes, but is not limited to:

- bash -x / xtrace output
- debug diagnostics
- comments
- empty lines
- waiver markers

---

### 3. WAIVER SEMANTICS

- WAIVER_APPLIED markers are NON-VIOLATING.
- Waived violations MUST NEVER increment violation counters.
- Waivers suppress enforcement, not visibility.

---

### 4. STDOUT / STDERR CONTRACT

- stdout is RESERVED for machine-parseable output only.
- stderr is RESERVED for diagnostics and debug output.
- Debug modes MUST route output away from stdout.

Violation of this contract invalidates parser correctness.

---

### 5. EXIT CODE SEMANTICS

The following exit code meanings are frozen:

- 0 : no violations (pass)
- 1 : one or more real violations (fail)
- >1 : execution or system error

These meanings MUST remain stable across all governance tooling.

---

### 6. EVIDENCE BUNDLE REQUIREMENT

All execution work MUST produce an evidence bundle containing:

- git status
- git diff --stat
- commands executed
- exit codes observed
- confirmation of verification targets

Narrative explanation is optional.
Evidence is mandatory.

---

(Removed 2026-08-27: a ROLE SEPARATION contract stood here defining
COG/OPER/AGENT roles. It conflicted outright with `HEE_EXECUTION_ATTRIBUTION.md`'s
different two-role AGENT/OPERATOR split -- same words, opposite meanings,
in two doctrine files in the same directory -- and matched nothing in real
practice, which just says "the human"/"the agent." Dropped rather than
adjudicated between two dead vocabularies; `HEE_EXECUTION_ATTRIBUTION.md`
was removed for the same reason in this same pass.)

## SOFT-FROZEN CONTRACTS

The following are frozen by convention but MAY evolve with PLAN + evidence:

- Canonical violation output formats
- Legacy violation format tolerance
- Test harness structure
- CI ergonomics and layout

---

## POSTCHECK — REQUIRED FILE LOCATIONS

After adoption of this document, the following MUST exist:

- docs/doctrine/FROZEN_CONTRACTS.md   (this file)
- ci/governance/check.sh              (enforcing parser + contracts)
- hee/governance/fixtures/               (covering waived and failing cases)
- .github/workflows/*governance*      (CI enforcing exit codes)

If any of the above are missing, governance correctness is not guaranteed.

---

## FINAL NOTE

Frozen contracts describe **what must not change**.
They do not describe how things are implemented.

Implementation MAY evolve.
Contracts MAY NOT, except by deliberate thaw with evidence.
