#!/usr/bin/env python3
"""PreToolUse(Bash): refuse a mutating git operation while HEAD is main.

This is the client-side half of the one rule that survived retiring the
`hee_git_ops.sh` wrapper on 2026-08-31: **never commit or push directly to
main**. Branch protection on the remote is the authoritative control -- it
is server-side and binds every operator, agent and machine equally. This
hook exists because branch protection can only reject the *push*, by which
point the commit already exists locally and has to be unwound.

Why this is not the wrapper again
---------------------------------
The retired wrapper failed because it stood between the agent and ordinary
git for *every* operation, demanded a `--reason` nothing ever read, and had
no op for half the real work. This hook does nothing except in one specific
situation -- a mutating git verb while HEAD is main -- and is otherwise
completely invisible. It adds no ceremony to the working path.

Fails open. If the branch cannot be determined, or anything raises, the
command is allowed: a guard that breaks unrelated work is worse than no
guard. Real precedent, same day: a hook that matched `git commit` inside a
sed pattern blocked a command that made no commit at all.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from _cmdparse import runs_git
except Exception:
    print(json.dumps({}))
    sys.exit(0)

PROTECTED = {"main", "master"}
MUTATING = {"commit", "push", "merge", "rebase", "cherry-pick", "revert", "reset"}


def allow():
    print(json.dumps({}))
    sys.exit(0)


def main() -> None:
    try:
        data = json.load(sys.stdin)
        command = data.get("tool_input", {}).get("command", "") or ""
    except Exception:
        allow()

    verb = runs_git(command, MUTATING)
    if not verb:
        allow()

    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if branch.returncode != 0:
            allow()  # not a repo, detached, or git unavailable
        current = branch.stdout.strip()
    except Exception:
        allow()

    if current not in PROTECTED:
        allow()

    reason = (
        f"Refusing `git {verb}` while HEAD is '{current}'. "
        "Work happens on a branch and lands through a PR -- "
        "PROMPTING_RULES.md rule 1.\n\n"
        f"    git switch -c feature/<short-description>\n"
        f"    # then re-run your git {verb}\n\n"
        "Branch protection on the remote enforces this server-side; this "
        "hook catches it before the commit exists locally, so there is "
        "nothing to unwind."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
        "systemMessage": reason,
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
