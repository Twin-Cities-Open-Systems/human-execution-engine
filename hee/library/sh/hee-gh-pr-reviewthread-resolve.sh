#!/bin/sh
# hee-gh-pr-reviewthread-resolve.sh
# Resolve review threads by thread ID (GraphQL). Default is DRY RUN.
# Usage:
#   hee-gh-pr-reviewthread-resolve.sh --threads-file /path/to/threads.tsv [--apply]
# threads.tsv format: <thread_id>\t<comment_dbid>\t<snippet>

set -eu

THREADS_FILE=""
APPLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --threads-file) THREADS_FILE="$2"; shift 2 ;;
    --apply) APPLY=1; shift 1 ;;
    *) echo "🔴 unknown arg: $1" >&2; exit 2 ;;
  esac
done

test -n "$THREADS_FILE" || { echo "🔴 missing --threads-file" >&2; exit 2; }
test -f "$THREADS_FILE" || { echo "🔴 threads file not found: $THREADS_FILE" >&2; exit 2; }

command -v gh >/dev/null 2>&1 || { echo "🔴 gh missing" >&2; exit 2; }

MUT='mutation($threadId:ID!){resolveReviewThread(input:{threadId:$threadId}){thread{id isResolved}}}'

echo '# STATUS'
echo "🟦 threads_file=$THREADS_FILE"
echo "🟦 apply=$APPLY (0=dry-run, 1=resolve)"

while IFS="$(printf '\t')" read -r TID _rest; do
  test -n "$TID" || continue
  echo
  echo "🟦 thread_id=$TID"
  if [ "$APPLY" -eq 1 ]; then
    gh api graphql -f query="$MUT" -F threadId="$TID" >/dev/null
    echo "🟩 resolved"
  else
    echo "🟨 dry-run (use --apply to resolve)"
  fi
done <"$THREADS_FILE"
