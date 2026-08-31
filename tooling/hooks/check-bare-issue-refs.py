#!/usr/bin/env python3
"""PreToolUse(Bash): warn when a commit/issue/PR body uses a bare `#N`.

Bare `#N` is ambiguous across a multi-repo workspace and mis-renders --
it auto-links against whatever repo context the renderer assumes. The
canonical form is a short label linked to the full URL,
`[repo#N](https://github.com/<owner>/<repo>/(issues|pull)/<n>)`, settled by
operator measurement 2026-08-31 (PROMPTING_RULES.md rule 3).

Two real defects fixed 2026-08-31, both hit in one session:

1. It scanned the ENTIRE command string, so it matched `git commit` inside a
   `sed` replacement pattern and blocked a command that made no commit --
   then flagged an unrelated `#1` in the same text. It now inspects only the
   `-m`/`--message`/`--body`/`--title` values, via `_cmdparse`, and only when
   git/gh is genuinely in command position.

2. It was a hard `deny`. A reference-formatting nit is not worth blocking
   work over, and it blocked an attempt to write the very rule that explains
   not to write bare `#N` -- the rule text has to quote the bad form. It now
   warns: the signal survives, the failure mode does not.

Fails open on any internal error. This is a nudge, never a gate.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from _cmdparse import commit_message_text, invocations
except Exception:
    print(json.dumps({}))
    sys.exit(0)

# Bare #<digits>: not already qualified (repo#12, issue:12) and not part of
# a URL path (/issues/12, /pull/12).
BARE = re.compile(r"(?<![:/\w])#\d+")


def quiet():
    print(json.dumps({}))
    sys.exit(0)


def is_body_writing_command(command: str) -> bool:
    """True only when git/gh is in command position writing a lasting body."""
    for argv in invocations(command):
        prog = argv[0].rsplit("/", 1)[-1]
        rest = [a for a in argv[1:] if not a.startswith("-")]
        if prog == "git" and rest and rest[0] == "commit":
            return True
        if prog == "gh" and len(rest) >= 2 and rest[0] in ("issue", "pr") \
                and rest[1] in ("create", "comment", "close", "edit"):
            return True
    return False


def main() -> None:
    try:
        data = json.load(sys.stdin)
        command = data.get("tool_input", {}).get("command", "") or ""
    except Exception:
        quiet()

    if not is_body_writing_command(command):
        quiet()

    body = commit_message_text(command)
    if not body:
        quiet()  # heredoc or -F file: not visible here, by design

    hits = BARE.findall(body)
    if not hits:
        quiet()

    msg = (
        f"Heads up: bare {hits[0]} in a commit/issue/PR body. Bare #N is "
        "ambiguous across this multi-repo workspace and auto-links against "
        "whatever repo the renderer assumes.\n"
        "Canonical form (PROMPTING_RULES rule 3, settled by measurement "
        "2026-08-31): [repo#N](https://github.com/<owner>/<repo>/issues/<n>) "
        "-- or issue:N@repo in structured YAML.\n"
        "Not blocking: if you are quoting the bad form on purpose, as rule "
        "text often must, carry on."
    )
    print(json.dumps({"systemMessage": msg}))
    sys.exit(0)


if __name__ == "__main__":
    main()
