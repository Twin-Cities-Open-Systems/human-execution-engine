"""hee_cli -- uniform ``help`` handling for every hee tool written in Python.

Python sibling of ``library/bash/cli.help.shfn.bash``, the same way
``hee_status`` is the Python sibling of ``vis.status.shfn.bash``. Same three
properties, same ``--`` semantics, same stderr channel for the discard note,
so a shell tool and a Python tool answer ``help`` indistinguishably.

THE RULE, operator 2026-08-31: "make sure help works everywhere and when
found, does help on prev verb/etc and not exec anything to right".

Three properties, in order of how much they cost when violated:

 1. ``help``, ``--help`` and ``-h`` all work, from ANY position in argv.
 2. Help is for the verb chain to the LEFT of the help token, so
    ``hee check refs help`` documents ``refs``, not ``check``.
 3. NOTHING TO THE RIGHT OF THE HELP TOKEN IS EXECUTED. This is the safety
    property. A tool that scans only ``argv[0]``, or only the last argument,
    will happily run ``hee ticket help --force`` as a real ``--force``.
    Asking for help must never be able to do anything.

Why this exists, and why argparse is not enough
-----------------------------------------------
``argparse`` owns ``-h``/``--help`` but not the bare ``help`` verb, and it
resolves them only after it has parsed -- and in a subparser layout, after it
has already accepted or rejected everything to the right. Measured
2026-09-01 by ``hee check cli``: of 54 hee tools, 1 conformed. 24 of the 37
CRITICAL ones are Python, and 8 of those exited non-zero for ``--help``
itself, because argparse errored on an unrelated argument before it ever got
to the help flag.

So the check must run BEFORE the parser is built, on raw ``sys.argv[1:]``.
That is what this module is for.

Usage in a tool::

    import sys
    from pathlib import Path
    sys.path.insert(
        0, str(Path(__file__).resolve().parent.parent.parent / "library" / "py")
    )
    from hee_cli import help_wanted, help_topic, note_ignored

    def main(argv: list[str]) -> int:
        if help_wanted(argv):
            note_ignored(argv)
            usage_for(help_topic(argv))
            return 0
        ...                      # only now build the parser

    raise SystemExit(main(sys.argv[1:]))

``argv`` is the argument list WITHOUT the program name -- the direct
equivalent of shell's ``"$@"``.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

__all__ = [
    "HELP_TOKENS",
    "help_wanted",
    "help_left",
    "help_verbs",
    "help_topic",
    "help_ignored",
    "note_ignored",
]

#: The three spellings, matching ``cli.help.shfn.bash`` exactly.
HELP_TOKENS = ("help", "--help", "-h")

#: POSIX end-of-options. A ``help`` after it is a literal operand, not a
#: request for help -- so ``hee print -- help`` prints the word "help".
_END_OF_OPTIONS = "--"


def help_wanted(argv: Sequence[str]) -> bool:
    """True if any argument is a help token. Scans the WHOLE argv, not argv[0].

    Stops at ``--``: everything after it is an operand, never a help request.
    """
    for arg in argv:
        if arg in HELP_TOKENS:
            return True
        if arg == _END_OF_OPTIONS:
            return False
    return False


def help_left(argv: Sequence[str]) -> list[str]:
    """Everything strictly to the LEFT of the first help token, unfiltered.

    Everything from the token rightward is deliberately discarded -- that is
    property 3, and discarding it here is what makes it impossible to run.

    Flags are kept, unlike :func:`help_verbs`, because some tools spell their
    actions as flags: ``hee-ticket -close help`` must resolve to the
    ``-close`` page, and a verbs-only view cannot see it.
    """
    left: list[str] = []
    for arg in argv:
        if arg in HELP_TOKENS or arg == _END_OF_OPTIONS:
            break
        left.append(arg)
    return left


def help_verbs(argv: Sequence[str]) -> list[str]:
    """The verb chain to the LEFT of the first help token.

    Flags are not verbs and are skipped -- use :func:`help_left` when a tool's
    actions are spelled as flags.
    """
    return [a for a in help_left(argv) if not a.startswith("-")]


def help_topic(argv: Sequence[str]) -> str:
    """The deepest verb -- what a tool usually dispatches its usage on.

    Empty string when help was asked for at the top level.
    """
    verbs = help_verbs(argv)
    return verbs[-1] if verbs else ""


def help_ignored(argv: Sequence[str]) -> list[str]:
    """What was to the RIGHT of the help token -- the part that was NOT run."""
    seen = False
    ignored: list[str] = []
    for arg in argv:
        if seen:
            ignored.append(arg)
        elif arg in HELP_TOKENS:
            seen = True
    return ignored


def note_ignored(argv: Sequence[str], stream=None) -> None:
    """Tell the operator, on stderr, that the rest of the line was discarded.

    Operator, 2026-08-31, on seeing the discard proved in a table: "add that
    to the output, check that in future". Silence here is the failure mode --
    someone types ``hee ticket help --force``, gets a help page, and has no
    way to know whether ``--force`` ran. Saying so converts an invisible
    safety property into a visible one.

    stderr, not stdout, so ``hee foo help | ...`` still pipes clean help text.
    """
    ignored = help_ignored(argv)
    if not ignored:
        return
    print(
        "ℹ️  NOTE  not executed (right of the help token): " + " ".join(ignored),
        file=stream if stream is not None else sys.stderr,
    )
