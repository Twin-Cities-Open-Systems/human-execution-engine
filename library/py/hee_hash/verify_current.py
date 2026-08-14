#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from hee_hash.soa import verify_current_host


def main() -> int:
    # Real gotcha, found 2026-08-14: socket.getfqdn() (soa.py's default
    # when now_hostf is None) silently misresolves on any host whose
    # /etc/hosts aliases the short hostname on the 127.0.0.1/localhost
    # line ahead of the real FQDN line -- getfqdn() returns "localhost"
    # instead, and verify_current_host() then looks for
    # ~/.hee/current/soa/localhost.legs.kv, which doesn't exist. Fixing
    # /etc/hosts is the real fix; HEE_HOSTF is the escape hatch for
    # hosts where that hasn't happened yet (or can't, e.g. no root).
    hostf_override = os.environ.get("HEE_HOSTF") or None
    try:
        r = verify_current_host(Path.home(), now_hostf=hostf_override)
    except FileNotFoundError as e:
        print(f"ERR: {e}", file=sys.stderr)
        print(
            "hint: if this path uses 'localhost' where you expected a real "
            "hostname, socket.getfqdn() is misresolving this host (often an "
            "/etc/hosts ordering issue -- short hostname aliased on the "
            "127.0.0.1 line ahead of the real FQDN line). Fix /etc/hosts, "
            "or set HEE_HOSTF=<real.fqdn> as a workaround.",
            file=sys.stderr,
        )
        return 2
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
