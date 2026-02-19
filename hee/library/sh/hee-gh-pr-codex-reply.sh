#!/bin/sh
# hee-gh-pr-codex-reply.sh
# Purpose: reply to Codex PR review comments (REST, paginated)
# Default behavior: dry-run (prints targets). Use --apply to post replies.

REPO=""
PR=""
APPLY="no"
BODY="ACK. Tracking. Pagination/cursor completeness fix landed."

CODEX_LOGIN_PREFIX="chatgpt-codex-connector"
ONLY_IDS=""

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --pr) PR="$2"; shift 2 ;;
    --apply) APPLY="yes"; shift 1 ;;
    --body) BODY="$2"; shift 2 ;;
    --codex-login-prefix) CODEX_LOGIN_PREFIX="$2"; shift 2 ;;
    --comment-ids) ONLY_IDS="$2"; shift 2 ;; # space-separated numeric ids
    -h|--help)
      echo "usage: $0 --repo owner/name --pr <num> [--apply] [--body text] [--comment-ids \"id id id\"]"
      break
      ;;
    *) echo "unknown arg: $1"; break ;;
  esac
done

if [ -z "$REPO" ] || [ -z "$PR" ]; then
  echo "missing --repo or --pr"
else
  command -v gh >/dev/null 2>&1 || echo "missing gh"
  command -v jq >/dev/null 2>&1 || echo "missing jq"

  COMMENTS="$(gh api --paginate "repos/$REPO/pulls/$PR/comments" \
    | jq -r --arg p "$CODEX_LOGIN_PREFIX" '
      .[]
      | select((.user.login|tostring|ascii_downcase|startswith($p)) or (.user.login|tostring|ascii_downcase|contains("codex")))
      | (.id|tostring)
    ')"

  if [ -n "$ONLY_IDS" ]; then
    # filter to ONLY_IDS
    FILTERED=""
    for cid in $COMMENTS; do
      echo "$ONLY_IDS" | grep -q -w "$cid" && FILTERED="$FILTERED $cid" || true
    done
    COMMENTS="$FILTERED"
  fi

  for CID in $COMMENTS; do
    echo "codex_review_comment_id=$CID apply=$APPLY"
    if [ "$APPLY" = "yes" ]; then
      gh api --method POST "repos/$REPO/pulls/$PR/comments/$CID/replies" -f body="$BODY" >/dev/null
      echo "🟦 reply_rc($CID)=$?"
    fi
  done
fi
