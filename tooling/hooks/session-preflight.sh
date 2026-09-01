#!/usr/bin/env sh
# SessionStart hook: report repo health at session open. Never gates.
#
# prompts/INIT.md has long claimed "session start is gated by
# ci/git/hee-preflight.sh". Nothing actually ran it, so the claim was
# aspirational. This makes it true in the only form that is safe: it
# *reports*, it never blocks.
#
# Four footguns this deliberately designs around, all named before it was
# written (operator asked "footgun?" -- the answer was yes, four):
#
#  1. Central blast radius. One bad edit to the preflight script would
#     otherwise break session start for every operator in every repo at
#     once, with no PR gate between the edit and everyone feeling it. So
#     this can only ever emit text -- there is no failure path that stops
#     a session starting.
#  2. Path assumption. hee-preflight.sh is HEE-relative; in any other
#     repo's cwd it does not exist. Guarded, silent no-op when absent.
#  3. Latency on every session. Hard timeout, and skipped entirely if
#     `timeout` is unavailable rather than risking a hang.
#  4. Noise decay. Preflight prints a FAIL block per problem. Dumping that
#     every session means it stops being read within a day -- worse than
#     nothing. So this summarises: the count and the first line only.
#
# Emits SessionStart additionalContext, or nothing at all.

set -u

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
PF="$REPO_ROOT/ci/git/hee-preflight.sh"

[ -x "$PF" ] || exit 0
command -v timeout >/dev/null 2>&1 || exit 0
command -v jq >/dev/null 2>&1 || exit 0

OUT=$(cd "$REPO_ROOT" && timeout 10s "$PF" 2>&1)
RC=$?

# 124 = timed out. Say so rather than reporting a false clean.
if [ "$RC" -eq 124 ]; then
  jq -nc '{hookSpecificOutput:{hookEventName:"SessionStart",
    additionalContext:"PREFLIGHT: ⚠️ WARNING timed out after 10s -- state unknown, not clean. Run ci/git/hee-preflight.sh manually."}}'
  exit 0
fi

[ "$RC" -eq 0 ] && exit 0

FIRST=$(printf '%s\n' "$OUT" | grep -m1 -E '^(FAIL|ERROR|WARN)' || printf '%s' "preflight exited $RC")
COUNT=$(printf '%s\n' "$OUT" | grep -cE '^(FAIL|ERROR)' || true)
[ "${COUNT:-0}" -eq 0 ] && COUNT=1

jq -nc --arg first "$FIRST" --arg n "$COUNT" --arg root "$REPO_ROOT" '
  {hookSpecificOutput:{hookEventName:"SessionStart",
   additionalContext:("PREFLIGHT: ❌ CRITICAL " + $n + " issue(s) in " + $root
     + ". First: " + $first
     + "\nThis is a report, not a gate -- the session is running. Run ci/git/hee-preflight.sh for the full detail. Broken state is the task, not a side note.")}}'
exit 0
