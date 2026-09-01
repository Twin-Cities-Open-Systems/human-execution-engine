#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from hee_hash.soa import verify_current_host


def main() -> int:
    r = verify_current_host(Path.home())
    # ordered, heelang-ish fields
    print("# VERIFY hee://_")
    print(f"hash_spec_id={r.hash_spec_id}")
    print(f"hash_algo={r.hash_algo}")
    print(f"host={r.host}")
    print(f"host_short={r.host_short}")
    print(f"legs_path={r.legs_path}")
    print(f"yaml_path={r.yaml_path}")
    print(f"expected_stool={r.expected_stool_full or 'MISSING'}")
    print(f"observed_stool={r.stool_full}")
    print(f"observed_show={r.stool_show}")
    print(f"ok={str(r.ok).lower()}")

    if not r.ok:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
