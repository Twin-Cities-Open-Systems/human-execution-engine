# GCIC Contract: hee-measure.v1

Scope: Defines the data contract for `apiVersion: hee/v1` `kind: Measure`.

This contract governs Measure payload shape + invariants. Execution behavior (ingest, emit paths, determinism) is covered by `hee-ingest-io.v1`.

## 1) Envelope (MUST)

All Measure objects MUST satisfy the hee-object envelope:

- `apiVersion: hee/v1`
- `kind: Measure`
- `metadata.name` is kebab-case
- `metadata.labels` MUST include:
  - `hee.object: "true"`
  - `hee.tcos/env: test|prod`
  - `hee.tcos/topic: <domain>` (e.g. `finance`, `ops`)

Everything else is optional/extensible.

## 2) spec vs status

- `spec`: payload/content (the measurement)
- `status`: reserved for gate outcomes, validation summaries, reconciliation, etc.

## 3) Canonical spec fields (alpha-stable)

- `spec.measure`: names the measurement type (string)
- `spec.flow.type`: `snapshot|delta`
- `spec.ts`: timestamps (raw + normalized as available)
- `spec.context`: provenance + identity for the measure source
- optional substructures for domain payloads, e.g.:
  - finance: `amount`, `legs`, `instrument`, `order`, `pricing`, `positions_*`
  - ops/metrics: `value` or `series`

## 4) Raw-first normalization (MUST)

Prefer staged representations:
- `*_raw`: verbatim source strings
- `*_dec`: numeric stored as string (avoid float rounding)
- fixed-point ints when safe:
  - `*_cents`, `*_micros`, etc.

Do not invent values not present in the source. If a value/leg is not derivable, represent it as absent/unknown explicitly (e.g. `state: absent`, or `null`).

## 5) Metrics (ops + finance both allowed)

Canonical metric representations:
- `spec.measure: metric.sample` (single datapoint)
- `spec.measure: metric.series` (time-range chunk)

Unknown value handling:
- unknown/NaN MUST remain unknown (YAML `null`); never coerced to 0.

RRD mapping details live in `hee/measure/rrd.md` and are governed by `hee-ingest-io.v1` for emit behavior.

## 6) RFC3339++ timestamps (policy)

- Keep raw time strings (`*_raw`) when present.
- When normalized, use RFC3339 with explicit timezone.
- For RRD exports, normalized timestamps MUST be UTC `...Z` when derived from epoch seconds.

## 7) References

- Schema: `schemas/hee/v1/measure.schema.json` (alpha)
- Related contract: `hee/gcic/contracts/hee-ingest-io.v1.md`
