"""CLI conformance checks for this org's own `hee-*` tools.

Real trigger, 2026-08-31. The operator ran:

    for sub in $(hee list | sed 1,4d | cut -d- -f2 | cut -d' ' -f1 | sort -u); do
        echo "testing == $sub =="; hee $sub help
    done

and hit `hee lint help` printing `🔴 🟦 b # ERROR: not in a git repo`. Two
separate defects in one line: help was gated behind a git-repo check it does
not need, and the failure was reported in BARE COLOR, which rule 11 forbids.
His ask was to make it "better and catch problems", so this is the sweep
version of that loop.

WHY THIS RUNS FROM A NON-REPO DIRECTORY. That is the whole point. `hee lint
help` is fine from inside a checkout and only breaks outside one, so a
checker that runs in the repo it is checking cannot see the bug the operator
actually hit. Every probe here runs in a temp dir.

WHY `help`, `--help` AND `-h` ARE ALL PROBED. Operator, 2026-08-31: "on cli
`hee-git-merge` is `hee git-merge` this is true on all cli cmds afaik" -- the
surface is expected to be uniform. A tool where `-h` works but `help` does
not is a tool whose help is undiscoverable to someone typing the obvious
thing; `hee-git-merge help` is exactly that case (argparse rejects the bare
word and exits 2).
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from typing import Any

VERBS = ("help", "--help", "-h")
TIMEOUT = 10

# Property 3's probe. Appended AFTER a help token to prove the tool does not
# parse or execute what follows. Deliberately an unknown FLAG, never a real
# one: this checker must never be able to trigger a destructive action in the
# tool it is checking, so the probe is inert by construction.
SENTINEL = "--hee-clicheck-sentinel-must-not-be-parsed"

# The note hee_help_note_ignored() prints when it discards arguments.
IGNORED_NOTE = re.compile(r"not executed \(right of the help token\)")

# Text that means the tool ERRORED rather than printed help.
ERROR_MARKERS = re.compile(
    r"not in a git repo|Traceback \(most recent|unrecognized arguments|"
    r"No such file or directory|command not found|Permission denied|"
    r"unknown predicate|Illegal option",
    re.I,
)

# Rule 11: status must ship icon+LABEL, never a bare color. These glyphs
# carry color and nothing else, so their presence without an adjacent
# OK/WARNING/CRITICAL/UNKNOWN word is the violation.
BARE_COLOR = re.compile(r"[\U0001F534\U0001F535\U0001F7E2\U0001F7E1\U0001F7E6\U0001F7E5]")
STATUS_WORD = re.compile(r"\b(OK|WARNING|CRITICAL|UNKNOWN|WARN|CRIT|UNKN)\b")

SEV = {"OK": 0, "WARNING": 1, "CRITICAL": 2, "UNKNOWN": 3}

# Structure that only a real help page has.
HELP_SHAPE = re.compile(r"^\s*(SYNOPSIS|DESCRIPTION|USAGE|OPTIONS|EXIT STATUS)\s*$|^usage:",
                        re.M | re.I)


def looks_like_help(out: str) -> bool:
    """Is this a help page, or an error message?

    Needed because ERROR_MARKERS matches DOCUMENTATION too. Real false
    positive, caught 2026-08-31 before this check ever shipped: hee-worktree's
    help contains the line

        1 WARNING   not in a git repo, git refused the operation, or no

    as its EXIT STATUS prose, and the checker reported the tool as broken. A
    checker that cries wolf about correct tools is worse than no checker --
    rule 16's "never add a check that is red on day one" is the same lesson.
    """
    return bool(HELP_SHAPE.search(out)) and len(out.splitlines()) >= 5


def discover_tools(bindir: str) -> list[str]:
    """Every executable `hee-*` in bindir, de-duplicated by subcommand name.

    A `.py` sibling is not a separate tool: `hee-fields` and `hee-fields.py`
    are one subcommand, and probing both would double-count its failures.
    """
    seen: dict[str, str] = {}
    for name in sorted(os.listdir(bindir)):
        if not name.startswith("hee-"):
            continue
        path = os.path.join(bindir, name)
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            continue
        seen.setdefault(re.sub(r"\.py$", "", name), path)
    return [seen[k] for k in sorted(seen)]


def probe(path: str, verb: str, cwd: str) -> dict[str, Any]:
    """Run one tool with one help verb and record exactly what came back."""
    try:
        p = subprocess.run(
            [path, verb], cwd=cwd, capture_output=True, text=True,
            timeout=TIMEOUT,
            # A help probe must never inherit a session that makes it pass by
            # accident, and must never block on a prompt.
            stdin=subprocess.DEVNULL,
        )
        return {"rc": p.returncode, "out": (p.stdout or "") + (p.stderr or ""),
                "timeout": False}
    except subprocess.TimeoutExpired:
        return {"rc": None, "out": "", "timeout": True}
    except OSError as exc:
        return {"rc": None, "out": f"OSError: {exc}", "timeout": False}


def probe_tail(path: str, verb: str, cwd: str) -> dict[str, Any]:
    """Run `tool <verb> SENTINEL` to prove nothing right of help is executed."""
    try:
        p = subprocess.run(
            [path, verb, SENTINEL], cwd=cwd, capture_output=True, text=True,
            timeout=TIMEOUT, stdin=subprocess.DEVNULL,
        )
        return {"rc": p.returncode, "out": (p.stdout or "") + (p.stderr or ""),
                "timeout": False}
    except subprocess.TimeoutExpired:
        return {"rc": None, "out": "", "timeout": True}
    except OSError as exc:
        return {"rc": None, "out": f"OSError: {exc}", "timeout": False}


def errored(r: dict) -> bool:
    """True only for a genuine error, not for help that mentions one."""
    out = r.get("out") or ""
    if not ERROR_MARKERS.search(out):
        return False
    return not (r.get("rc") == 0 and looks_like_help(out))


def judge(tool: str, results: dict[str, dict]) -> dict[str, Any]:
    """Turn raw probe output into findings. Severity reflects real cost."""
    findings: list[tuple[str, str]] = []
    working = [v for v, r in results.items() if v != "_tail"
               and r["rc"] == 0 and r["out"].strip() and not errored(r)]

    for verb, r in results.items():
        if verb == "_tail":
            continue
        if r["timeout"]:
            findings.append(("CRITICAL", f"`{verb}` hung (>{TIMEOUT}s) -- help must never block"))
            continue
        out = r["out"]
        if errored(r):
            first = next((ln.strip() for ln in out.splitlines() if ln.strip()), "")
            findings.append(("CRITICAL", f"`{verb}` errored instead of printing help: {first[:70]}"))
        elif r["rc"] != 0:
            findings.append(("CRITICAL", f"`{verb}` exited {r['rc']}, expected 0"))
        elif not out.strip():
            findings.append(("CRITICAL", f"`{verb}` printed nothing"))

        # Exit 0 with error text is the SILENT form -- worse than a loud
        # failure, because CI and humans both read 0 as success.
        if r["rc"] == 0 and errored(r):
            findings.append(("CRITICAL", f"`{verb}` errored but exited 0 -- silently passes CI"))

        if r["rc"] is not None and r["rc"] not in (0, 1, 2, 3):
            findings.append(("WARNING", f"`{verb}` exit {r['rc']} is outside the Nagios range 0-3"))

        if BARE_COLOR.search(out) and not STATUS_WORD.search(out):
            findings.append(("WARNING", f"`{verb}` uses a bare color glyph with no status label (rule 11)"))

    if working and len(working) < len(VERBS):
        missing = ", ".join(f"`{v}`" for v in VERBS if v not in working)
        findings.append(("WARNING", f"help is not uniform -- {missing} does not work but "
                                    f"`{working[0]}` does"))

    # --- Property 3: nothing to the right of the help token is executed ---
    tail = results.get("_tail")
    if tail is not None and working:
        if tail["timeout"]:
            findings.append(("CRITICAL", f"`help {SENTINEL}` hung -- it is parsing past the help token"))
        else:
            # The NOTE line legitimately ECHOES the discarded arguments, so a
            # naive `SENTINEL in out` flags a correctly-behaving tool. Real
            # false positive, caught on hee-check itself 2026-08-31 -- the
            # first tool to adopt the contract was reported as violating it.
            # Look for the sentinel only OUTSIDE the note it is quoted in.
            body = "\n".join(ln for ln in tail["out"].splitlines()
                              if not IGNORED_NOTE.search(ln))
            if SENTINEL in body or (tail["rc"] not in (0, None) and errored(tail)):
                findings.append(("CRITICAL",
                                 "arguments AFTER the help token are still parsed -- "
                                 "`help --force` would run --force"))
            elif not IGNORED_NOTE.search(tail["out"]):
                findings.append(("WARNING",
                                 "discards arguments after the help token but does not say so -- "
                                 "use hee_help_note_ignored()"))

    if working:
        best = results[working[0]]["out"]
        if "SYNOPSIS" not in best:
            findings.append(("WARNING", "help has no SYNOPSIS section"))
        if "EXIT" not in best.upper():
            findings.append(("WARNING", "help documents no EXIT STATUS"))

    level = "OK"
    for lv, _ in findings:
        if SEV[lv] > SEV[level]:
            level = lv
    return {"tool": tool, "level": level, "findings": findings,
            "verbs_working": working}


def check(bindir: str) -> dict[str, Any]:
    """Probe every hee tool. Runs in a temp dir so a repo-gated help is caught."""
    tools = discover_tools(bindir)
    reports = []
    with tempfile.TemporaryDirectory(prefix="hee-clicheck-") as cwd:
        for path in tools:
            sub = re.sub(r"\.py$", "", os.path.basename(path))[len("hee-"):]
            results = {v: probe(path, v, cwd) for v in VERBS}
            # Probe property 3 against whichever help verb actually works,
            # so a tool is not penalised twice for a help verb it lacks.
            live = next((v for v in VERBS
                         if results[v]["rc"] == 0 and results[v]["out"].strip()
                         and not errored(results[v])), None)
            if live:
                results["_tail"] = probe_tail(path, live, cwd)
            reports.append(judge(sub, results))
    worst = "OK"
    for r in reports:
        if SEV[r["level"]] > SEV[worst]:
            worst = r["level"]
    return {
        "bindir": bindir,
        "total": len(reports),
        "ok": sum(1 for r in reports if r["level"] == "OK"),
        "worst": worst,
        "reports": reports,
    }
