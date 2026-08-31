"""Shared shell-command parsing for PreToolUse hooks.

Why this exists
---------------
A hook that greps the whole command string for a phrase produces real false
positives. Observed 2026-08-31: a hook matched the literal text `git commit`
*inside a sed replacement pattern* and blocked an unrelated command. The
command was `sed -i 's|...git commit/push/merge...|...|' file` -- no commit
was being made at all.

The fix is to look at *command position*, not substring presence. A shell
command line is split on separators, and only the first word of each segment
is the program actually being run.

This is deliberately a small heuristic, not a shell parser. It is used to
decide whether to warn or block, so it errs toward not matching: a missed
detection is a hook that stays quiet, which is much cheaper than a hook that
blocks work it should not.
"""

from __future__ import annotations

import re
import shlex

__all__ = ["segments", "invocations", "runs_git", "commit_message_text"]

# Split on shell separators that start a new command position.
_SEPARATORS = re.compile(r"(?:\|\||&&|[;\n|])")


def segments(command: str) -> list[str]:
    """Split a command line into candidate command positions."""
    return [s.strip() for s in _SEPARATORS.split(command or "") if s.strip()]


def invocations(command: str) -> list[list[str]]:
    """Tokenised argv for each segment. Unparseable segments are skipped."""
    out: list[list[str]] = []
    for seg in segments(command):
        try:
            argv = shlex.split(seg)
        except ValueError:
            continue  # unbalanced quotes -- not our business
        if not argv:
            continue
        # step over leading env assignments: FOO=bar git push
        i = 0
        while i < len(argv) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", argv[i]):
            i += 1
        if i < len(argv):
            out.append(argv[i:])
    return out


def runs_git(command: str, subcommands: set[str]) -> str | None:
    """Return the git subcommand actually being invoked, if any.

    Only matches when `git` is the program in a command position AND the
    subcommand is one of `subcommands`. Substring occurrences inside quoted
    arguments -- sed patterns, echo text, commit bodies -- do not match.
    """
    for argv in invocations(command):
        if argv[0] != "git" and not argv[0].endswith("/git"):
            continue
        for tok in argv[1:]:
            if tok.startswith("-"):
                continue  # global flags like -C <path>, --no-pager
            return tok if tok in subcommands else None
    return None


def commit_message_text(command: str) -> str:
    """Extract only the message body of a commit/issue/PR mutation.

    Returns the -m/--message/--body/--title values, not the whole command
    line, so a rule about message content cannot fire on unrelated argv.
    Heredoc-fed and -F file bodies are invisible here by design -- better to
    miss those than to inspect the entire command string.
    """
    parts: list[str] = []
    for argv in invocations(command):
        take = False
        for tok in argv:
            if take:
                parts.append(tok)
                take = False
                continue
            if tok in ("-m", "--message", "--body", "--title"):
                take = True
            elif tok.startswith(("--message=", "--body=", "--title=")):
                parts.append(tok.split("=", 1)[1])
    return "\n".join(parts)
