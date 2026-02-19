#!/bin/sh
# hee-gh-pr-codex-list.sh
# Purpose: list Codex PR review comments (REST, paginated) + unresolved Codex review threads (GraphQL, cursor-paginated)
# Outputs (in --outdir, default .):
#   codex.comments.tsv
#   codex.unresolved-threads.tsv

REPO=""
PR=""
OUTDIR="."
CODEX_LOGIN_PREFIX="chatgpt-codex-connector"

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --pr) PR="$2"; shift 2 ;;
    --outdir) OUTDIR="$2"; shift 2 ;;
    --codex-login-prefix) CODEX_LOGIN_PREFIX="$2"; shift 2 ;;
    -h|--help)
      echo "usage: $0 --repo owner/name --pr <num> [--outdir dir] [--codex-login-prefix prefix]"
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

  mkdir -p "$OUTDIR" 2>/dev/null || true

  OWNER="$(printf '%s' "$REPO" | awk -F/ '{print $1}')"
  NAME="$(printf '%s' "$REPO" | awk -F/ '{print $2}')"

  COMMENTS_TSV="$OUTDIR/codex.comments.tsv"
  THREADS_TSV="$OUTDIR/codex.unresolved-threads.tsv"

  : > "$COMMENTS_TSV"
  : > "$THREADS_TSV"

  # REST: PR review comments (paginated)
  gh api --paginate "repos/$REPO/pulls/$PR/comments" \
    | jq -r --arg p "$CODEX_LOGIN_PREFIX" '
      .[]
      | select((.user.login|tostring|ascii_downcase|startswith($p)) or (.user.login|tostring|ascii_downcase|contains("codex")))
      | [
          (.id|tostring),
          (.user.login|tostring),
          (.path|tostring),
          ((.line // .original_line // .position // 0)|tostring),
          (.created_at|tostring),
          (.html_url|tostring)
        ]
      | @tsv
    ' > "$COMMENTS_TSV"

  # GraphQL: reviewThreads(first:100, after:$after) cursor-pagination
  QUERY='
    query($owner:String!, $name:String!, $pr:Int!, $after:String) {
      repository(owner:$owner, name:$name) {
        pullRequest(number:$pr) {
          reviewThreads(first: 100, after: $after) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id
              isResolved
              comments(first: 50) {
                nodes {
                  databaseId
                  author { login }
                  path
                  originalLine
                  createdAt
                  body
                }
              }
            }
          }
        }
      }
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

    # append unresolved codex-ish threads to TSV:
    printf '%s\n' "$RESP" | jq -r --arg p "$CODEX_LOGIN_PREFIX" '
      .data.repository.pullRequest.reviewThreads.nodes[]
      | select(.isResolved == false)
      | . as $t
      | ($t.comments.nodes // []) as $cs
      | ($cs | map(select((.author.login|tostring|ascii_downcase|startswith($p)) or (.author.login|tostring|ascii_downcase|contains("codex")) or (.body|tostring|ascii_downcase|contains("p2 badge")))) ) as $codex
      | select(($codex|length) > 0)
      | ($codex[0]) as $c
      | [
          ($t.id|tostring),
          ($c.databaseId|tostring),
          ($c.author.login|tostring),
          ($c.path|tostring),
          ($c.originalLine|tostring),
          ($c.createdAt|tostring)
        ]
      | @tsv
    ' >> "$THREADS_TSV"

    HAS_NEXT="$(printf '%s\n' "$RESP" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage')"
    AFTER="$(printf '%s\n' "$RESP" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor // ""')"
    [ "$AFTER" = "null" ] && AFTER=""
  done
fi
