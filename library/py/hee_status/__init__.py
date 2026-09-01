"""hee_status -- the one status vocabulary for every HEE tool.

Python sibling of ``library/bash/vis.status.shfn.bash``. Same levels, same
exit codes, same ``HEE_STATUS_STYLE`` environment variable, so a shell tool
and a Python tool are indistinguishable in a log or a pipe.

Why Nagios
----------
``OK`` / ``WARNING`` / ``CRITICAL`` / ``UNKNOWN`` with exit codes 0/1/2/3 is
the Nagios plugin API -- a real, long-standing standard, already the framing
in ``docs/specs/HEE_HARDWARE_DISCOVERY.md``. Adopted rather than invented.

Before this existed, HEE tooling spoke six overlapping vocabularies at once
(``PASS``/``FAIL``/``OK``/``WARN``/``ERROR``/``SUCCESS``) across 39 files,
with emoji chosen ad hoc per script -- some with no text label at all, which
is the rule 11 failure this replaces.

Rule 11 compliance
------------------
Every line carries an icon **and** a text label, never color alone, and the
icons are shape-distinct (check / triangle / cross / question) rather than
three identical circles differing only in hue.

Machine parsing
---------------
Parse the LABEL, never the icon. The icon is presentation and is expected to
change. Real regression this prevents: ``hee-index`` parsed ``hee-lint``'s
emoji as its status field, which froze the icons until it was decoupled.

Usage
-----
    from hee_status import Status, status, emit

    emit(Status.OK, "everything is fine")
    raise SystemExit(status("CRITICAL"))     # -> exit 2
"""

from __future__ import annotations

import enum
import os
import sys

__all__ = ["Status", "status", "render", "emit", "demo"]


class Status(enum.Enum):
    """Nagios plugin API levels. The value IS the process exit code."""

    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3

    @property
    def icon(self) -> str:
        return {
            Status.OK: "✅",        # check mark
            Status.WARNING: "⚠️",  # warning triangle
            Status.CRITICAL: "❌",  # cross mark
            Status.UNKNOWN: "❓",   # question mark
        }[self]


# Legacy words normalize in, so callers can migrate without a flag day.
# Color words are accepted only for migration -- never name a hue in new
# code; name a severity.
_ALIASES = {
    "OK": Status.OK, "PASS": Status.OK, "SUCCESS": Status.OK, "GREEN": Status.OK,
    "WARN": Status.WARNING, "WARNING": Status.WARNING, "YELLOW": Status.WARNING,
    "CRIT": Status.CRITICAL, "CRITICAL": Status.CRITICAL, "ERROR": Status.CRITICAL,
    "FAIL": Status.CRITICAL, "FAILED": Status.CRITICAL, "RED": Status.CRITICAL,
}


def status(level) -> Status:
    """Normalize anything callerish into a Status. Unknown input -> UNKNOWN."""
    if isinstance(level, Status):
        return level
    return _ALIASES.get(str(level).strip().upper(), Status.UNKNOWN)


def render(level, message: str = "") -> str:
    """One status line in the caller's configured style."""
    lvl = status(level)
    msg = message or "(no message)"
    style = os.environ.get("HEE_STATUS_STYLE", "icon").lower()

    if style == "plain":
        return f"{lvl.name} {msg}"
    if style == "ascii":
        short = {"OK": "OK", "WARNING": "WARN", "CRITICAL": "CRIT", "UNKNOWN": "UNKN"}[lvl.name]
        return f"[{short}]".ljust(7) + msg
    return f"{lvl.icon} {lvl.name} {msg}"


def emit(level, message: str = "", stream=None) -> Status:
    """Print one status line; return the Status so it can drive an exit code."""
    lvl = status(level)
    if stream is None:
        stream = sys.stderr if lvl is not Status.OK else sys.stdout
    print(render(lvl, message), file=stream)
    return lvl


def demo() -> None:
    """Preview every level in the caller's current style."""
    print(f"HEE_STATUS_STYLE={os.environ.get('HEE_STATUS_STYLE', 'icon (default)')}\n")
    for lvl, msg in (
        (Status.OK, "everything is fine"),
        (Status.WARNING, "something needs a look"),
        (Status.CRITICAL, "something is broken"),
        (Status.UNKNOWN, "could not determine state"),
    ):
        print(render(lvl, msg))
    print("\nOther styles: icon | ascii | plain  (set HEE_STATUS_STYLE in your heerc)")


if __name__ == "__main__":
    demo()
