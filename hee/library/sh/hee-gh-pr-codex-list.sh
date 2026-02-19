#!/bin/sh
# hee-gh-pr-codex-list.sh
# List Codex review comments + unresolved review threads for a PR.
# Usage:
#   hee-gh-pr-codex-list.sh --repo owner/repo --pr N [--workdir /tmp/x]
#
# Outputs:
#   $WORKDIR/codex.comments.tsv           (comment_id \t path \t line \t snippet)
#   $WORKDIR/codex.unresolved-threads.tsv (thread_id \t comment_dbid \t snippet)

set -eu

REPO=""
PR=""
WORKDIR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --pr) PR="$2"; shift 2 ;;
    --workdir) WORKDIR="$2"; shift 2 ;;
    *) echo "🔴 unknown arg: $1" >&2; exit 2 ;;
  esac
done

test -n "$REPO" || { echo "🔴 missing --repo" >&2; exit 2; }
test -n "$PR"   || { echo "🔴 missing --pr" >&2; exit 2; }

command -v gh >/dev/null 2>&1 || { echo "🔴 gh missing" >&2; exit 2; }
command -v jq >/dev/null 2>&1 || { echo "🔴 jq missing" >&2; exit 2; }

if [ -z "$WORKDIR" ]; then WORKDIR="$(mktemp -d)"; fi

COMMENTS_JSON="$WORKDIR/review-comments.json"
THREADS_JSON="$WORKDIR/threads.json"
OUT_COMMENTS="$WORKDIR/codex.comments.tsv"
OUT_THREADS="$WORKDIR/codex.unresolved-threads.tsv"

echo '# STATUS'
echo "🟦 repo=$REPO"
echo "🟦 pr=$PR"
echo "🟦 workdir=$WORKDIR"

echo
echo '# ACTION (pull review comments)'
gh api -H 'Accept: application/vnd.github+json' "repos/$REPO/pulls/$PR/comments" >"$COMMENTS_JSON"

jq -r '
  .[]
  | select(.user.login=="chatgpt-codex-connector")
  | [
      (.id|tostring),
      (.path // ""),
      ((.line // 0)|tostring),
      ((.body|gsub("[\r\n]+";" ")|.[0:90]) // "")
    ] | @tsv
' "$COMMENTS_JSON" >"$OUT_COMMENTS" || true

echo "🟦 codex_comment_count=$(wc -l <"$OUT_COMMENTS" | tr -d " ")"
sed -n '1,10p' "$OUT_COMMENTS" || true

echo
echo '# ACTION (pull unresolved review threads via graphql)'
cat >"$WORKDIR/q.graphql" <<'Q'
query($owner:String!, $name:String!, $pr:Int!) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$pr) {
      reviewThreads(first:100) {
        nodes {
          id
          isResolved
          comments(first:50) {
            nodes {
              databaseId
              author { login }
              body
            }
          }
        }
      }
    }
  }
}
Q

OWNER="$(echo "$REPO" | cut -d/ -f1)"
NAME="$(echo "$REPO" | cut -d/ -f2)"

gh api graphql \
  -F owner="$OWNER" \
  -F name="$NAME" \
  -F pr="$PR" \
  -f query="$(cat "$WORKDIR/q.graphql")" \
  >"$THREADS_JSON"

jq -r '
  .data.repository.pullRequest.reviewThreads.nodes[]
  | select(.isResolved==false)
  | . as $t
  | ($t.comments.nodes | map(select(.author.login=="chatgpt-codex-connector")) | .[0]) as $c
  | select($c != null)
  | [
      $t.id,
      ($c.databaseId|tostring),
      (($c.body|gsub("[\r\n]+";" ")|.[0:90]) // "")
    ] | @tsv
' "$THREADS_JSON" >"$OUT_THREADS" || true

echo "🟦 codex_unresolved_thread_count=$(wc -l <"$OUT_THREADS" | tr -d " ")"
sed -n '1,10p' "$OUT_THREADS" || true

echo
echo '# NEXT'
echo "🟦 comments=$OUT_COMMENTS"
echo "🟦 threads=$OUT_THREADS"
