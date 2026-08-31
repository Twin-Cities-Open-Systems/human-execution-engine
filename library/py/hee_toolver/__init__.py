"""hee_toolver -- determine a tool's version, and prove it is a version.

Why this exists
---------------
Two real defects, 2026-08-31, both from guessing instead of validating:

1. `sh --version` prints ``sh: 0: Illegal option --`` and exits 2. A naive
   probe recorded that error message AS the version string. It even
   replayed consistently, because the error is deterministic -- so
   "it reproduces" was not enough to catch it.

2. `tmux --version` is not a tmux flag; tmux uses ``-V``. A Makefile used
   ``--version`` and captured the usage block instead of a version.

So a version claim needs two things a bare probe does not give:
  * a NON-ZERO EXIT IS NEVER A VERSION, and
  * the captured text must actually LOOK like a version.

VERSION_RE requires at least ``<digits>.<digits>``. That is what separates
``tmux 3.4`` and ``jq-1.7`` from ``sh: 0: Illegal option --``, which
contains a digit but no dotted version.

Flag discovery
--------------
When a tool answers none of the usual flags, `discover_flag` reads its own
``-h``/``--help`` and looks for a documented version option rather than
brute-forcing further. That is how a tool like tmux tells you it wants
``-V``, if you bother to ask it.

Never runs a tool with no argument. `hee-gen-manpages` was observed
installing a pre-commit hook as a side effect of generating documentation
(issue 464); this library only ever passes an explicit flag.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

__all__ = ["VERSION_RE", "Probe", "looks_like_version", "probe", "discover_flag"]

# At least major.minor. A bare digit is not a version -- that is exactly the
# shape of "sh: 0: Illegal option --".
#
# The lookbehind excludes only digits and dots, NOT letters: a leading "v" is
# extremely common ("version v4.53.3") and an earlier stricter lookbehind
# rejected yq's real version for exactly that reason, then fell through to
# `yq -v` -- which on yq means VERBOSE, not version. That turned on debug
# logging and emitted a timestamp, from which a "version" of 16.691-05 was
# extracted. Two failures compounding: a wrongly-rejected good answer, then
# a wrongly-accepted bad one.
VERSION_RE = re.compile(r"(?<![\d.])v?\d+\.\d+(?:\.\d+)*(?:[-+~][\w.]+)?(?![\d.])")

# A timestamp contains dotted digits and will otherwise satisfy VERSION_RE.
# Reject before matching rather than after, so a verbose-mode log line can
# never be mistaken for a version.
_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}|\d{2}:\d{2}:\d{2}")

CANDIDATE_FLAGS = ("--version", "-V", "-v", "version")
HELP_FLAGS = ("--help", "-h", "-?")

# In a help text, a line mentioning version is expected to name its flag.
_HELP_VERSION_LINE = re.compile(
    r"^\s*(?P<flags>-[-\w?]+(?:\s*,\s*-[-\w?]+)*)\s+.*\bversion\b", re.IGNORECASE | re.MULTILINE
)


@dataclass(frozen=True)
class Probe:
    tool: str
    path: str | None
    flag: str | None        # the flag that actually worked
    raw: str | None         # first line captured
    version: str | None     # the substring matching VERSION_RE
    stream: str | None      # stdout | stderr
    returncode: int | None
    reason: str             # why this outcome, in words


def looks_like_version(text: str) -> str | None:
    """Return the version substring, or None. Never guesses."""
    if not text:
        return None
    if _TIMESTAMP_RE.search(text):
        return None
    m = VERSION_RE.search(text)
    return m.group(0).lstrip("vV") if m else None


def _run(argv: list[str], timeout: int = 5):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None


def discover_flag(path: str) -> str | None:
    """Ask the tool's own help which flag reports its version."""
    for hf in HELP_FLAGS:
        r = _run([path, hf])
        if r is None:
            continue
        text = (r.stdout or "") + (r.stderr or "")
        if not text.strip():
            continue
        for m in _HELP_VERSION_LINE.finditer(text):
            for f in re.split(r"\s*,\s*", m.group("flags").strip()):
                if f.startswith("-"):
                    return f
    return None


def probe(tool: str, extra_flags: tuple[str, ...] = ()) -> Probe:
    path = shutil.which(tool)
    if not path:
        return Probe(tool, None, None, None, None, None, None, "not installed")

    tried: list[str] = []
    for flag in tuple(extra_flags) + CANDIDATE_FLAGS:
        if flag in tried:
            continue
        tried.append(flag)
        r = _run([path, flag])
        if r is None:
            continue
        if r.returncode != 0:
            continue                      # an error is never a version
        for stream, txt in (("stdout", r.stdout), ("stderr", r.stderr)):
            line = next((l.strip() for l in (txt or "").splitlines() if l.strip()), "")
            if not line:
                continue
            ver = looks_like_version(line)
            if ver:
                return Probe(tool, path, flag, line, ver, stream, r.returncode,
                             "matched VERSION_RE on a zero-exit invocation")

    # Nothing standard worked -- ask the tool's own help what it wants.
    found = discover_flag(path)
    if found and found not in tried:
        r = _run([path, found])
        if r is not None and r.returncode == 0:
            for stream, txt in (("stdout", r.stdout), ("stderr", r.stderr)):
                line = next((l.strip() for l in (txt or "").splitlines() if l.strip()), "")
                ver = looks_like_version(line) if line else None
                if ver:
                    return Probe(tool, path, found, line, ver, stream, r.returncode,
                                 f"flag discovered from the tool's own help: {found}")

    return Probe(tool, path, None, None, None, None, None,
                 f"no flag produced a string matching VERSION_RE (tried: {', '.join(tried)}"
                 + (f"; help suggested {found}" if found else "; help suggested nothing") + ")")
