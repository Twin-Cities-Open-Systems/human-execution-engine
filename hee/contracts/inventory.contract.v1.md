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
- inv.lifecycle: planned | ordered | received | in_service | repurpose | retired  (inventory.asset only)
- inv.sub: food | sundry | building | tools | vehicle | metal | electronics | unknown

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

`stableid` never changes over the life of an asset. It is, in order:
1. an id assigned before the item exists or arrives -- for network hardware,
   its `lan-host` name from `hee-name` (an item planned today has no serial);
2. else the serial number, lowercased, when the item is in hand at record time;
3. else `asset_type`-`tsz`, the record's own observed time.

A serial learned later is added to `spec.asset.serial`; the name stays.

## Asset records

`spec.asset` for `inventory.asset`. Rendered by `hee inv add` from a
`hee.inventory.asset-request.v1` JSON document, which is also what the
inventory page's add form submits.

- name (MUST): the human label, 1-80 characters
- asset_type (MUST): a token, `^[a-z0-9][a-z0-9-]{0,39}$` (firewall, camera, drive)
- lifecycle (MUST), mirrored as the label `inv.lifecycle`:
  - planned     decided on, not bought; no purchase, serial or evidence yet
  - ordered     bought, not in hand
  - received    in hand, not in service
  - in_service  doing its job
  - repurpose   in hand, waiting for a new job
  - retired     out of service, kept or disposed
- stableid (MUST): see Naming
- vendor, model, serial (MAY; null when unknown)
- interfaces[] (MAY): `{role: wired|wireless, mac}`, MAC lowercase colon form
- requirements[] (MAY): buying or install criteria, for planned items
- refs[] (MAY): URLs to the decision or spec behind the record
- notes (MAY)

A planned asset carries no evidence. It is not an unknown: its bucket and
sub are known, so the unknown gates below do not apply to it.

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
