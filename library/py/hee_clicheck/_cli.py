"""CLI backend for `hee-check cli`. Thin, per rule 13 -- logic is in the
package so it stays testable."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hee_clicheck import SEV, check  # noqa: E402

STYLE = os.environ.get("HEE_STATUS_STYLE", "icon")
ICON = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "❌", "UNKNOWN": "❓"}
SHORT = {"OK": "OK", "WARNING": "WARN", "CRITICAL": "CRIT", "UNKNOWN": "UNKN"}


def line(level: str, msg: str, indent: str = "") -> None:
    if STYLE == "plain":
        print(f"{indent}{level} {msg}")
    elif STYLE == "ascii":
        print(f"{indent}[{SHORT[level]}]".ljust(len(indent) + 7) + msg)
    else:
        print(f"{indent}{ICON[level]} {level} {msg}")


def main() -> int:
    args = (os.environ.get("HEE_CLICHECK_ARGS") or "").split()
    want_json = "--json" in args
    quiet = "--quiet" in args
    # _cli.py -> hee_clicheck -> py -> library -> repo root. Four levels;
    # three lands on library/ and silently reports "no such tool directory".
    _root = os.path.abspath(__file__)
    for _ in range(4):
        _root = os.path.dirname(_root)
    bindir = next((a for a in args if not a.startswith("-")), None) or \
        os.path.join(_root, "tooling", "bin")

    if not os.path.isdir(bindir):
        line("UNKNOWN", f"no such tool directory: {bindir}")
        return 3

    rep = check(bindir)

    if want_json:
        print(json.dumps(rep, indent=2, sort_keys=True, default=str))
        return SEV[rep["worst"]]

    for r in sorted(rep["reports"], key=lambda x: (-SEV[x["level"]], x["tool"])):
        if r["level"] == "OK":
            if not quiet:
                line("OK", f"{r['tool']}: help conforms")
            continue
        line(r["level"], f"{r['tool']}")
        for lv, msg in r["findings"]:
            line(lv, msg, indent="      ")

    bad = rep["total"] - rep["ok"]
    print()
    line(rep["worst"] if bad else "OK",
         f"{rep['ok']}/{rep['total']} hee tools have conforming help"
         + (f" -- {bad} need work" if bad else ""))
    return SEV[rep["worst"]]


if __name__ == "__main__":
    sys.exit(main())
