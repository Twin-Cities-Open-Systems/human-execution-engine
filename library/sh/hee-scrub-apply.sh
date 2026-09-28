#!/bin/sh
# hee-scrub-apply.sh
# Purpose: rewrite history to remove a leaked path, then force-push rewritten mirror (GitHub-safe).
# Usage:
#   hee-scrub-apply.sh --repo-slug owner/repo --leak-path path/in/repo --workdir /tmp/x
#
# Notes:
# - Requires git-filter-repo.
# - Deletes local refs/pull/* and any non heads/tags refs before mirror push (GitHub denies hidden refs).
# - Does not guarantee GitHub-managed PR caches are purged; see verify script + Support guidance.

REPO_SLUG=""
LEAK_PATH=""
WORKDIR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --repo-slug) REPO_SLUG="$2"; shift 2 ;;
    --leak-path) LEAK_PATH="$2"; shift 2 ;;
    --workdir) WORKDIR="$2"; shift 2 ;;
    *) echo "🔴 unknown arg: $1"; shift ;;
  esac
done

echo '# STATUS'
echo "🟦 repo_slug=$REPO_SLUG"
echo "🟦 leak_path=$LEAK_PATH"
echo "🟦 workdir=$WORKDIR"

test -n "$WORKDIR" && echo "🟩 workdir set" || echo "🔴 missing --workdir"
command -v git-filter-repo >/dev/null 2>&1 && echo "🟩 git-filter-repo present" || echo "🔴 missing git-filter-repo"

MIRROR_DIR="${WORKDIR}/repo.mirror"
echo "🟦 mirror=$MIRROR_DIR"
test -d "$MIRROR_DIR" && echo "🟩 mirror exists" || echo "🔴 mirror missing (run precheck)"

cd "$MIRROR_DIR" 2>/dev/null || echo "🔴 cd failed"

echo
echo '# VERIFY (origin matches)'
ORIGIN_URL="$(git remote get-url origin 2>/dev/null)"
echo "🟦 origin=$ORIGIN_URL"
echo "$ORIGIN_URL" | grep -F "$REPO_SLUG" >/dev/null 2>&1 && ORIGIN_OK=1 || ORIGIN_OK=0
test "$ORIGIN_OK" -eq 1 && echo "🟩 origin matches" || echo "🔴 origin mismatch (HALT)"

echo
echo '# ACTION (rewrite history: remove leaked path)'
TS="$(date -u +%Y%m%dT%H%M%SZ)"
FILTER_LOG="${WORKDIR}/git-filter-repo.${TS}.log"
echo "🟦 log=$FILTER_LOG"
if test "$ORIGIN_OK" -eq 1; then
  git filter-repo --force --invert-paths --path "$LEAK_PATH" >"$FILTER_LOG" 2>&1
  echo "🟦 filter_repo_rc=$?"
  echo "🟦 filter-repo tail:"
  tail -n 30 "$FILTER_LOG"
fi

echo
echo '# VERIFY (object scan: filename should not appear)'
if test "$ORIGIN_OK" -eq 1; then
  OBJLIST="${WORKDIR}/objects.all.txt"
  git rev-list --objects --all >"$OBJLIST"
  grep -F "$(basename "$LEAK_PATH")" "$OBJLIST" >/dev/null 2>&1 && echo "🔴 found filename in object list" || echo "🟩 filename not found (expected)"
  echo "🟦 grep_rc=$?"
fi

echo
echo '# ACTION (delete local PR refs + non heads/tags refs)'
if test "$ORIGIN_OK" -eq 1; then
  # refs/pull/*
  PULL_REFS_TXT="${WORKDIR}/pull-refs.txt"
  git for-each-ref refs/pull --format='%(refname)' >"$PULL_REFS_TXT"
  if test -s "$PULL_REFS_TXT"; then
    while IFS= read -r R; do
      git update-ref -d "$R"
    done <"$PULL_REFS_TXT"
  fi

  # any other refs except heads/tags
  OTHER_REFS_TXT="${WORKDIR}/other-refs.txt"
  git for-each-ref --format='%(refname)' | grep -Ev '^refs/(heads|tags)/' >"$OTHER_REFS_TXT"
  if test -s "$OTHER_REFS_TXT"; then
    while IFS= read -r R; do
      git update-ref -d "$R"
    done <"$OTHER_REFS_TXT"
  fi

  echo "🟩 local ref cleanup done"
fi

echo
echo '# ACTION (force-push rewritten mirror)'
if test "$ORIGIN_OK" -eq 1; then
  git push --force --mirror origin
  echo "🟦 push_rc=$?"
fi

echo
echo '# NEXT'
echo "🟦 Run verify script. If mirror clone still shows refs/pull/* retain the leak, GitHub Support purge is required."
echo "🟦 filter-repo log: $FILTER_LOG"
