#!/bin/sh
# hee-scrub-verify-remote.sh
# Purpose: verify scrub status on (a) normal clone surface and (b) mirror surface (includes GitHub PR refs).
# Usage:
#   hee-scrub-verify-remote.sh --repo-slug owner/repo --leak-path path/in/repo

REPO_SLUG=""
LEAK_PATH=""

while [ $# -gt 0 ]; do
  case "$1" in
    --repo-slug) REPO_SLUG="$2"; shift 2 ;;
    --leak-path) LEAK_PATH="$2"; shift 2 ;;
    *) echo "🔴 unknown arg: $1"; shift ;;
  esac
done

echo '# STATUS'
echo "🟦 repo_slug=$REPO_SLUG"
echo "🟦 leak_path=$LEAK_PATH"

WORKDIR="$(mktemp -d)"
echo "🟦 workdir=$WORKDIR"

echo
echo '# VERIFY (normal clone surface)'
git clone "git@github.com:${REPO_SLUG}.git" "$WORKDIR/normal" >/dev/null 2>&1
cd "$WORKDIR/normal" 2>/dev/null || echo "🔴 cd failed"
git log --all -n 5 --oneline -- "$LEAK_PATH" || true
echo "🟦 normal_gitlog_rc=$?"

echo
echo '# VERIFY (mirror surface: PR refs may retain old commits)'
cd "$WORKDIR" 2>/dev/null || true
git clone --mirror "git@github.com:${REPO_SLUG}.git" "$WORKDIR/mirror" >/dev/null 2>&1
cd "$WORKDIR/mirror" 2>/dev/null || echo "🔴 cd failed"
git log --all -n 10 --oneline -- "$LEAK_PATH" || true
echo "🟦 mirror_gitlog_rc=$?"
OBJLIST="$WORKDIR/objects.all.txt"
git rev-list --objects --all >"$OBJLIST"
grep -F "$(basename "$LEAK_PATH")" "$OBJLIST" >/dev/null 2>&1 && echo "🔴 mirror still retains filename (likely via refs/pull/* caches)" || echo "🟩 mirror filename not found (clean)"
echo "🟦 mirror_grep_rc=$?"

echo
echo '# NEXT'
echo "🟦 If mirror retains filename, GitHub Support purge is required for cached PR diffs/refs/pull/*."
echo "🟦 workdir=$WORKDIR (keep for evidence if needed)"
