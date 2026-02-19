#!/bin/sh
# hee-gh-pr-reviewthread-resolve.sh
# Purpose: resolve unresolved Codex review threads (GraphQL, cursor-paginated)
# Default behavior: dry-run. Use --apply to resolve.

REPO=""
PR=""
APPLY="no"
CODEX_LOGIN_PREFIX="chatgpt-codex-connector"

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --pr) PR="$2"; shift 2 ;;
    --apply) APPLY="yes"; shift 1 ;;
    --codex-login-prefix) CODEX_LOGIN_PREFIX="$2"; shift 2 ;;
    -h|--help)
      echo "usage: $0 --repo owner/name --pr <num> [--apply]"
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

  OWNER="$(printf '%s' "$REPO" | awk -F/ '{print $1}')"
  NAME="$(printf '%s' "$REPO" | awk -F/ '{print $2}')"

  QUERY='
    query($owner:String!, $name:String!, $pr:Int!, $after:String) {
      repository(owner:$owner, name:$name) {
        pullRequest(number:$pr) {
          reviewThreads(first: 100, after: $after) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id
              isResolved
              comments(first: 50) { nodes { author { login } body } }
            }
          }
        }
      }
    }
  '

  MUT='
    mutation($threadId:ID!) {
      resolveReviewThread(input:{threadId:$threadId}) { thread { id isResolved } }
    }
  '

  AFTER=""
  HAS_NEXT="true"

  while [ "$HAS_NEXT" = "true" ]; do
    if [ -n "$AFTER" ]; then
      RESP="$(gh api graphql -f query="$QUERY" -F owner="$OWNER" -F name="$NAME" -F pr="$PR" -F after="$AFTER")"
    else
      RESP="$(gh api graphql -f query="$QUERY" -F owner="$OWNER" -F name="$NAME" -F pr="$PR")"
    fi

    THREAD_IDS="$(printf '%s\n' "$RESP" | jq -r --arg p "$CODEX_LOGIN_PREFIX" '
      .data.repository.pullRequest.reviewThreads.nodes[]
      | select(.isResolved == false)
      | select(((.comments.nodes // []) | map(select((.author.login|tostring|ascii_downcase|startswith($p)) or (.author.login|tostring|ascii_downcase|contains("codex")) or (.body|tostring|ascii_downcase|contains("p2 badge")))) | length) > 0)
      | .id
    ')"

    for TID in $THREAD_IDS; do
      echo "thread_id=$TID apply=$APPLY"
      if [ "$APPLY" = "yes" ]; then
        gh api graphql -f query="$MUT" -F threadId="$TID" >/dev/null
        echo "🟦 resolve_rc($TID)=$?"
      fi
    done

    HAS_NEXT="$(printf '%s\n' "$RESP" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage')"
    AFTER="$(printf '%s\n' "$RESP" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor // ""')"
    [ "$AFTER" = "null" ] && AFTER=""
  done
fi
