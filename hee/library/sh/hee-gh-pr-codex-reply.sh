#!/bin/sh
# hee-gh-pr-codex-reply.sh
# Reply to Codex review comments on a PR with targeted “what we will do” messages.
# Default is DRY RUN. Use --apply to actually post replies.
#
# Usage:
#   hee-gh-pr-codex-reply.sh --repo owner/repo --pr N [--workdir /tmp/x] [--apply]

set -eu

REPO=""
PR=""
WORKDIR=""
APPLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --pr) PR="$2"; shift 2 ;;
    --workdir) WORKDIR="$2"; shift 2 ;;
    --apply) APPLY=1; shift 1 ;;
    *) echo "🔴 unknown arg: $1" >&2; exit 2 ;;
  esac
done

test -n "$REPO" || { echo "🔴 missing --repo" >&2; exit 2; }
test -n "$PR"   || { echo "🔴 missing --pr" >&2; exit 2; }

command -v gh >/dev/null 2>&1 || { echo "🔴 gh missing" >&2; exit 2; }
command -v jq >/dev/null 2>&1 || { echo "🔴 jq missing" >&2; exit 2; }

if [ -z "$WORKDIR" ]; then WORKDIR="$(mktemp -d)"; fi
COMMENTS_JSON="$WORKDIR/review-comments.json"

echo '# STATUS'
echo "🟦 repo=$REPO"
echo "🟦 pr=$PR"
echo "🟦 workdir=$WORKDIR"
echo "🟦 apply=$APPLY (0=dry-run, 1=post)"

gh api -H 'Accept: application/vnd.github+json' "repos/$REPO/pulls/$PR/comments" >"$COMMENTS_JSON"

# targeted bodies (per Codex P1s)
BODY_FAIL_FAST="$(cat <<'B'
ACK — correct catch. We will harden the scrub scripts to fail-closed:
- If mirror dir is missing or `cd` fails: HALT immediately (no subsequent git commands in an unexpected directory).
- Add a “prove bare repo” check before rewrite/push (rev-parse --is-bare-repository=true).
We’ll leave this thread unresolved until the follow-up hardening PR lands, then resolve.
B
)"

BODY_REJECT_EMPTY="$(cat <<'B'
ACK — correct catch. We will reject empty required args so identity checks can’t be bypassed:
- Require non-empty --repo-slug/--leak-path/--workdir; otherwise HALT.
- Also treat origin mismatch as a hard stop (no rewrite/push).
We’ll leave this thread unresolved until the follow-up hardening PR lands, then resolve.
B
)"

BODY_ABORT_ON_FAIL="$(cat <<'B'
ACK — correct catch. We will abort on any rewrite failure:
- If git-filter-repo returns non-zero: HALT and skip ref cleanup / force-push.
- Emit a clear rc + log pointer for evidence.
We’ll leave this thread unresolved until the follow-up hardening PR lands, then resolve.
B
)"

BODY_GENERIC="$(cat <<'B'
ACK — we’ll address this in a follow-up hardening PR and keep the thread unresolved until it lands, then resolve.
B
)"

# iterate codex comments
jq -r '
  .[]
  | select(.user.login=="chatgpt-codex-connector")
  | [(.id|tostring), (.body|tostring)] | @tsv
' "$COMMENTS_JSON" | while IFS="$(printf '\t')" read -r CID BODY; do
  test -n "$CID" || continue

  RESP="$BODY_GENERIC"
  echo "$BODY" | grep -qi 'Fail fast' && RESP="$BODY_FAIL_FAST" || true
  echo "$BODY" | grep -qi 'Reject empty repo slug' && RESP="$BODY_REJECT_EMPTY" || true
  echo "$BODY" | grep -qi 'Abort when history rewrite' && RESP="$BODY_ABORT_ON_FAIL" || true

  echo
  echo "🟦 comment_id=$CID"
  echo "🟦 selected_reply=$(echo "$RESP" | head -n1)"

  if [ "$APPLY" -eq 1 ]; then
    gh api -X POST -H 'Accept: application/vnd.github+json' \
      "repos/$REPO/pulls/$PR/comments" \
      -f in_reply_to="$CID" \
      -f body="$RESP" >/dev/null
    echo "🟩 posted"
  else
    echo "🟨 dry-run (use --apply to post)"
  fi
done

echo
echo '# NEXT'
echo "🟦 After the fix PR merges, resolve threads via hee-gh-pr-reviewthread-resolve.sh"
