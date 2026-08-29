#!/usr/bin/env python3
# check-bare-issue-refs.py
# PreToolUse hook (Bash matcher): blocks a bare "#<digits>" reference
# inside a git commit message or a gh issue/pr create/comment/close
# body. Bare #N is ambiguous across a multi-repo workspace and known
# to mis-render (auto-links to the wrong repo) -- real regression
# caught live, 2026-08-29. Real fix: use issue:N@repo / pr:N@repo
# (PROMPTING_RULES.md rule #3's own notation) or a full github.com URL
# instead. Fails open on any internal error -- this is a safety net,
# never a reason to block an unrelated command.

import json
import re
import sys

try:
    data = json.load(sys.stdin)
    cmd = data.get("tool_input", {}).get("command", "")
except Exception:
    print(json.dumps({}))
    sys.exit(0)

# Only check commands that write a real, permanent message body.
if not re.search(r"\bgit\s+commit\b|\bgh\s+(issue|pr)\s+(create|comment|close)\b", cmd):
    print(json.dumps({}))
    sys.exit(0)

# Bare #<digits> -- not already qualified (issue:123@repo / pr:123@repo)
# and not part of a URL path (/issues/123, /pull/123).
matches = [m for m in re.findall(r"(?<![:/\w])#\d+", cmd)]

if matches:
    reason = (
        f"Bare {matches[0]} reference found in a git commit/gh mutation body. "
        "Bare #N is ambiguous across repos in this multi-repo workspace and known to "
        "mis-render (auto-links using whatever repo context is assumed). "
        "Use issue:N@repo / pr:N@repo notation (e.g. issue:416@human-execution-engine), "
        "or a full https://github.com/... URL instead."
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

print(json.dumps({}))
