# Operators — `human-execution-engine`

Shared conventions live in
[`docs/guides/OPERATOR_GUIDE.md`](docs/guides/OPERATOR_GUIDE.md) (this
repo hosts the central guide itself, since it's the root doctrine
source — see `docs/DOCUMENTATION_POLICY.md`'s platform-independence
note). This doc is only what's specific to this repo's own scripts.

## Card tooling

`hee/cards/` mixes `kind: Card`, `kind: Pill`, plain `.md` docs, and
detached `.asc` signature files that happen to end in `.yaml` — no
single schema. Two stages, per the shfn→sh→bash→py→go convention:

- **`library/bash/cards.scan.shfn.bash`** — fast counts only (source
  `library/bash/rg.scan.shfn.bash` first, then `cards_scan [dir]`).
  No parsing, can't crash on an odd file.
- **`tooling/bin/scan-hee-cards.py`** — full per-file classification
  (real YAML parsing, catches malformed files as data instead of
  crashing). `python3 tooling/bin/scan-hee-cards.py hee/cards/`.

Real run against the live `hee/cards/` corpus:
[`examples/scan-hee-cards-output.txt`](examples/scan-hee-cards-output.txt).

## MIB tooling

`cmd/hee/` is a Go CLI stub (`hee help`/`mark`/`sig`/`card` listed,
none implemented yet beyond `help`) — not yet operator-usable, tracked
separately, not documented here as if it were real.
