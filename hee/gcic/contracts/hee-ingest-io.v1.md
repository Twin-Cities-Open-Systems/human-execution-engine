# GCIC Contract: hee-ingest-io.v1

Scope: Defines ingestion + emit semantics for hee objects (including `Measure`) using the `.hee` IO layout.

This contract is subordinate to GCIC and is compatible with DRIC; when DRIC is invoked, design and relay must obey its separation rules.

## 1) Directory semantics

- `~/.hee/in-take/` contains raw source inputs (bank exports, books exports, rrd files, etc.)
- `~/.hee/out-take/` contains emitted hee objects derived from in-take.

Buckets are a convenience only (not a schema requirement):
- `bank/`, `books/`, `fred/`, `tos/`, `trades/`, `rrd/`, etc.

## 2) Samples vs non-samples (MUST)

Any emitted object intended as a sample MUST include:
- `metadata.annotations.hee.sample: "true"`
- optional: `metadata.annotations.hee.sample.note`

Out-take SHOULD be treated as sample/test by default unless a run explicitly declares production intent.

## 3) verify-identity-before-emit (MUST)

Before any tool emits files (including writing into `~/.hee/out-take`), it MUST verify identity and target context.
The verification mechanism is allowed to evolve, but MUST:
- avoid relying on PWD alone
- ensure the operator and target paths are the intended ones
- fail safe (refuse to emit) on ambiguity

(Implementation detail can be anchored to the HEE SOA index file when available; this contract only states the invariant.)

## 4) Determinism (MUST)

Emit behavior MUST be deterministic:
- stable ordering: input-file order then row/time order
- stable naming scheme for `metadata.name`
- do not infer missing values (unknown stays unknown)
- preserve raw strings; normalize only when unambiguous

## 5) Quarantine (SHOULD)

If a row/file cannot be parsed or is ambiguous:
- do not drop silently
- route to a quarantine mechanism (file or report)
- include counts in a run report (rows seen/emitted/quarantined)

## 6) RRD specifics

RRD ingest MUST:
- derive `step_sec`, DS identity, and RRA identity from `rrdtool info`
- export values via `rrdtool fetch` (or `xport`) without coercing unknowns
- represent unknowns as YAML `null`
- use UTC RFC3339 (`...Z`) for timestamps derived from epoch seconds

## 7) Related

- Data contract: `hee/gcic/contracts/hee-measure.v1.md`
