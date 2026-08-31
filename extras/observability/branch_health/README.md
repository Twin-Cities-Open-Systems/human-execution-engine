# Branch Health Monitor (Extras)

## Status

NON-CANONICAL / DEMO TOOLING (NOT ENFORCEMENT)

## Purpose

This tool provides a lightweight, human-readable report about local Git branch hygiene.
It is intended for demos and operator convenience only.

## Non-Authority

- This tool is **not** part of the HEE control plane.
- It does **not** grant authorization.
- HEE authority is granted only via explicit chat-line sentinel:
  `AUTHZ: APPROVED_TO_ACT`

## Notes / Limitations

- PR detection requires GitHub CLI (`gh`) and an authenticated session.
- Some metrics are heuristic and may not precisely match merge semantics.
- For authoritative governance, rely on doctrine and the repo’s enforcement scripts.

## Usage

From repo root:

```bash
python extras/observability/branch_health/branch_health_monitor.py
python extras/observability/branch_health/branch_health_monitor.py --watch 10
python extras/observability/branch_health/branch_health_monitor.py --report --save
```
