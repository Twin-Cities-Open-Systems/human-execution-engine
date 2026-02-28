# inventory.contract.v1

## Scope

Inventory datasets are stored as HEE Measures.

- apiVersion: hee/v1
- kind: Measure
- spec.measure:
  - inventory.purchase
  - inventory.stock
  - inventory.asset
  - (future) inventory.lot

Dataset repo (canonical data): tcos-plan-private/inventory/objects/

## Envelope invariants (MUST)

- metadata.labels.hee.object: "true"
- metadata.labels.hee.tcos/topic: inventory
- spec.context.soa.file_ref: "~/.hee/index/_.yaml#hee-soa.v1"

## Taxonomy (labels)

- inv.bucket: consumable | durable | commodity | unknown
- inv.sub: food | sundry | building | tools | vehicle | metal | unknown

## Location

Two-tier:
- labels (selector-fast): inv.loc0..inv.loc3
- spec.location.path[] (fine resolution)

Location token convention (v1):
- entity-dir-slot
  - `entity`-<n|s|e|w>-`slot`
  - examples: shelf-a-n-03, rack-2-e-11

Basement is the current macro location (v1 default):
- inv.loc0: basement

## Naming (deterministic)

- inventory.purchase: inv-purchase-`vendor`-`tsz`
- inventory.stock:    inv-stock-`vendor`-<purchase_tsz>-lNN-`slug`
- inventory.asset:    inv-asset-`sub`-`stableid`

## Evidence

Canonical truth is YAML in git. Evidence is content-addressed in the dataset repo:
- inventory/evidence/by-sha256/aa/bb/`sha`.`ext`

Image metadata policy:
- write XMP pointers (namespace "hee"), not full YAML:
  - hee:ObjectRef (repo-relative YAML path)
  - hee:Name (metadata.name)
  - hee:Measure (spec.measure)
- fallback: XMP sidecar when embedding is unsafe

## Unknown lifecycle + gates

Unknown is allowed at ingest time but must not linger.

- WARN if unknown age >= 7d
- CRIT if unknown age >= 14d

Age source: spec.ts.observed

CI policy (v1):
- Fail on CRIT (>=14d).
- WARN is reported but non-fatal (until tightened later).

## Retention

No purge. Git retention. Future sqz/rollups may be added later.
