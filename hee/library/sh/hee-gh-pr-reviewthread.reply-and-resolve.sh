#!/bin/sh
# hee-gh-pr-reviewthread.reply-and-resolve.sh
# Reply to review comments, then resolve threads. Uses:
# - REST: create reply for a review comment
# - GraphQL: resolveReviewThread / unresolveReviewThread

say() { printf "%s\n" "$*"; }
die() { say "🔴 $*"; exit 1; }

REPO_SLUG="${1:-}"; PR_NUM="${2:-}"
[ -n "$REPO_SLUG" ] || die "usage: $0 <owner/repo> <pr_number>"

command -v gh >/dev/null 2>&1 || die "gh missing"
command -v rg >/dev/null 2>&1 || die "rg missing"

# stdin: TSV with columns: thread_id<TAB>comment_id<TAB>body_file
while IFS="$(printf '\t')" read -r thread_id comment_id body_file; do
  [ -n "$thread_id" ] || continue
  [ -n "$comment_id" ] || die "missing comment_id for thread_id=$thread_id"
  [ -f "$body_file" ] || die "missing body_file=$body_file"

  BODY="$(cat "$body_file")"
  say "🟦 thread_id=$thread_id"
  say "🟦 comment_id=$comment_id"

  # Reply (REST)
  gh api -X POST "repos/$REPO_SLUG/pulls/$PR_NUM/comments/$comment_id/replies" -f body="$BODY" >/dev/null \
    || die "reply failed comment_id=$comment_id"
  say "🟩 replied"

  # Resolve (GraphQL)
  gh api graphql -f query='mutation($id:ID!){ resolveReviewThread(input:{threadId:$id}){ thread{ id isResolved } } }' \
    -f id="$thread_id" >/dev/null || die "resolve failed thread_id=$thread_id"
  say "🟩 resolved"
  say
done
