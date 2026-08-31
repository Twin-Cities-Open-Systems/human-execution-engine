"""CLI backend for hee-ver. Kept out of the shell script so the logic is
testable and the tool stays thin, per rule 13."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hee_toolver import (                                    # noqa: E402
    hardware, platform, session, version_of, verity_of, verify_records,
)

STYLE = os.environ.get("HEE_STATUS_STYLE", "icon")
ICON = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "❌", "UNKNOWN": "❓"}
CODE = {"OK": 0, "WARNING": 1, "CRITICAL": 2, "UNKNOWN": 3}
SHORT = {"OK": "OK", "WARNING": "WARN", "CRITICAL": "CRIT", "UNKNOWN": "UNKN"}


def line(level: str, msg: str) -> None:
    if STYLE == "plain":
        print(f"{level} {msg}")
    elif STYLE == "ascii":
        print(f"[{SHORT[level]}]".ljust(7) + msg)
    else:
        print(f"{ICON[level]} {level} {msg}")


def kv(d: dict, skip=("sources",)) -> None:
    for k, v in d.items():
        if k in skip or v in (None, "", []):
            continue
        print(f"    {k:<20} {v}")


def main() -> int:
    cmd = os.environ.get("HEE_VER_CMD", "all")
    args = (os.environ.get("HEE_VER_ARGS") or "").split()
    want_json = "--json" in args
    args = [a for a in args if a != "--json"]

    source = "auto"
    if "--source" in args:
        i = args.index("--source")
        if i + 1 < len(args):
            source = args[i + 1]
            del args[i:i + 2]

    out: dict = {}
    worst = "OK"

    def bump(level: str) -> None:
        nonlocal worst
        if CODE[level] > CODE[worst]:
            worst = level

    if cmd in ("tool", "all"):
        names = [a for a in args if not a.startswith("-")] or (
            ["bash", "git", "python3", "jq", "rg", "tmux"] if cmd == "all" else [])
        if cmd == "tool" and not names:
            line("UNKNOWN", "hee-ver tool needs at least one tool name")
            return 3
        tools = {}
        for n in names:
            r = version_of(n, source=source)
            tools[n] = r
            if not want_json:
                if not r["path"]:
                    line("CRITICAL", f"{n}: not installed"); bump("CRITICAL")
                elif r["conflict"]:
                    line("CRITICAL", f"{n}: sources CONFLICT -- self={r['self']} package={r['package']} path={r['path_version']}")
                    bump("CRITICAL")
                elif r["imprecise"]:
                    line("WARNING", f"{n}: {r['version']} (binary under-reports: package is {r['package']})")
                    bump("WARNING")
                else:
                    line("OK", f"{n}: {r['version']}  [{r['source_used']}]")
        out["tools"] = tools

    if cmd in ("platform", "all"):
        p = platform()
        out["platform"] = p
        if not want_json:
            line("OK" if p.get("sources") else "UNKNOWN",
                 f"platform: {p.get('distro') or p.get('kernel_name','unknown')} "
                 f"({', '.join(p.get('sources', []))})")
            kv(p)
        if not p.get("sources"):
            bump("UNKNOWN")

    if cmd in ("hardware", "all"):
        h = hardware()
        out["hardware"] = h
        if not want_json:
            if h.get("sources"):
                line("OK", f"hardware: {h.get('sys_vendor','?')} {h.get('product_name','?')} "
                           f"({', '.join(h['sources'])})")
                kv(h)
            else:
                line("UNKNOWN", "hardware: no DMI available (normal in a container)")
        if not h.get("sources"):
            bump("UNKNOWN")

    if cmd in ("session", "all"):
        s = session()
        out["session"] = s
        if not want_json:
            if "--signature" in args:
                print(f"\n---\n<sub>signed: session `{s['session_id']}` · pid `{s['pid']}` · "
                      f"tmux `{s['tmux_uri']}` · {s.get('gh_actor','?')}@{s['host']} · "
                      f"{s['timestamp']}</sub>")
            else:
                line("OK" if s["session_id"] != "unknown" else "UNKNOWN",
                     f"session: {s.get('gh_actor','?')}@{s['host']}")
                kv(s)
        if s["session_id"] == "unknown":
            bump("UNKNOWN")

    if cmd == "verity":
        targets = [a for a in args if not a.startswith("-")]
        if not targets:
            line("UNKNOWN", "hee-ver verity needs a file path")
            return 3
        res = {}
        for t in targets:
            v = verity_of(t)
            res[t] = v
            if not want_json:
                if v["error"]:
                    line("UNKNOWN", f"{t}: {v['error']}"); bump("UNKNOWN")
                elif v["enabled"]:
                    line("OK", f"{t}: fs-verity ENABLED")
                else:
                    line("WARNING", f"{t}: fs-verity not enabled "
                                    f"(kernel support: {v['kernel_support']})")
                    bump("WARNING")
        out["verity"] = res

    if cmd == "verify":
        path = next((a for a in args if not a.startswith("-")), None)
        rep = verify_records(path)
        out["verify"] = rep
        if not want_json:
            if rep.get("error"):
                line("UNKNOWN", rep["error"]); return 3
            for r in rep["results"]:
                if r["ok"]:
                    line("OK", f"{r['name']}: reproduces ({r['version']})")
                else:
                    line("CRITICAL", f"{r['name']}: NO LONGER REPRODUCES -- "
                                     f"recorded {r['recorded']!r}, now {r['actual']!r}")
                    bump("CRITICAL")
            line("OK" if worst == "OK" else "CRITICAL",
                 f"{rep['ok']}/{rep['total']} recorded claims still reproduce")

    if cmd not in ("tool", "platform", "hardware", "session", "verity", "verify", "all"):
        line("UNKNOWN", f"unknown subcommand: {cmd}")
        return 2

    if want_json:
        print(json.dumps(out, indent=2, sort_keys=True, default=str))

    return CODE[worst]


if __name__ == "__main__":
    sys.exit(main())
