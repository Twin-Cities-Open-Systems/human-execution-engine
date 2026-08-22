# `hee/contracts/`

The `apiVersion: hee/v1`, `kind: Contract` schema — real authority/
governance contracts, distinct from the legacy `contracts/` family at
repo root (see [that directory's own README](../../contracts/README.md)
for what belongs there instead: GPT/Oper/Relay lane governance, a
different, older schema with no `may`/`must`/`must_not` vocabulary).

This schema is used identically in this repo and in `fleet-ops`'
`hee/contracts/` — same vocabulary, same meaning, wherever a real
signed contract instance lives.

## The `may` / `must` / `must_not` / `does` vocabulary — authoritative source

**Real gap closed, 2026-08-21**: this vocabulary was designed around
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) (and its 2017
clarification, [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174)) —
the actual IETF standard defining precise, unambiguous meaning for
requirement-level keywords in technical specifications. Widely used
across real specs and RFCs for exactly this reason: it removes
ambiguity about whether a requirement is absolute, conditional, or
optional. This repo referenced that design intent without ever citing
the source — closing that now, not redefining anything.

**What HEE actually uses today** — checked against every real contract
in `hee/contracts/` (this repo) and `fleet-ops/hee/contracts/`, not
assumed: only the strongest tier of RFC 2119's vocabulary is in live
use.

| HEE key | RFC 2119/8174 term | Real meaning |
|---|---|---|
| `must` | MUST / SHALL / REQUIRED | An absolute requirement of the contract. |
| `must_not` | MUST NOT / SHALL NOT | An absolute prohibition. |
| `may` | MAY / OPTIONAL | Genuinely optional — the actor may exercise this, choosing not to is equally valid under the contract. |
| `does` | *(not an RFC 2119 term — HEE's own addition)* | States a **fact** about the actor's role, not a normative requirement. Use this when a line describes what an actor *is*, not what it's obligated to do. |

**Not yet in use anywhere real**: `should`/`should_not`/`recommended` —
RFC 2119's middle tier (a real recommendation, departure from which
needs real justification, short of an absolute requirement). Available
if a future contract genuinely needs that middle ground between `must`
and `may` — not added speculatively here.

One real adaptation worth being explicit about: RFC 2119 defines these
terms for **ALL-CAPS words in prose** ("the implementation MUST...");
HEE uses lowercase `must`/`must_not`/`may` as **YAML keys** holding a
list of statements, a structural adaptation of the same underlying
meaning, not a literal reproduction of the RFC's own prose convention.

## What belongs here

Real `kind: Contract` instances — authority grants, governance
boundaries, sovereignty relationships. See any existing file in this
directory for the real schema shape (`metadata`, `spec.status`,
`spec.ratification_evidence`, `spec.actors.<name>.{role,may,must_not,does}`,
`spec.boundaries`, `spec.known_gaps`).
