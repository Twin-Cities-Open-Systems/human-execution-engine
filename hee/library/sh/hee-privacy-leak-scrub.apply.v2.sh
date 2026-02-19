#!/bin/sh
# hee-privacy-leak-scrub.apply.v2.sh
# Purpose: APPLY step for privacy-leak scrubs, fail-fast and emit-proof.
# Notes:
# - No implicit reliance on PWD. Requires explicit mirror dir.
# - Halts on any precondition failure.
# - Halts if history rewrite fails or post-verify still finds the leak.

say() { printf "%s\n" "$*"; }
die() { say "🔴 $*"; exit 1; }

WORKDIR=""
MIRROR_DIR=""
REPO_SLUG=""
LEAK_PATH=""

while [ $# -gt 0 ]; do
  case "$1" in
    --workdir) WORKDIR="${2:-}"; shift 2 ;;
    --mirror) MIRROR_DIR="${2:-}"; shift 2 ;;
    --repo) REPO_SLUG="${2:-}"; shift 2 ;;
    --leak-path) LEAK_PATH="${2:-}"; shift 2 ;;
    *) die "unknown arg: $1" ;;
  esac
done

say "# STATUS"
say "🟦 workdir=$WORKDIR"
say "🟦 mirror=$MIRROR_DIR"
say "🟦 repo=$REPO_SLUG"
say "🟦 leak_path=$LEAK_PATH"
say

[ -n "$WORKDIR" ] || die "missing --workdir"
[ -n "$MIRROR_DIR" ] || die "missing --mirror"
[ -n "$REPO_SLUG" ] || die "missing --repo"
[ -n "$LEAK_PATH" ] || die "missing --leak-path"

[ -d "$MIRROR_DIR" ] || die "mirror dir missing: $MIRROR_DIR"
command -v git >/dev/null 2>&1 || die "git missing"
git filter-repo --help >/dev/null 2>&1 || die "git-filter-repo missing (install git-filter-repo)"

cd "$MIRROR_DIR" >/dev/null 2>&1 || die "cannot cd mirror: $MIRROR_DIR"
git rev-parse --is-bare-repository >/dev/null 2>&1 || die "not a git repo: $MIRROR_DIR"

ORIGIN="$(git remote get-url origin 2>/dev/null || true)"
say "# VERIFY (origin)"
say "🟦 origin=$ORIGIN"
echo "$ORIGIN" | rg -q "$REPO_SLUG" || die "origin mismatch (expected repo slug to match): $REPO_SLUG"
say "🟩 origin matches"
say

say "# ACTION (rewrite history: remove leaked path)"
git filter-repo --path "$LEAK_PATH" --invert-paths
RC=$?
[ $RC -eq 0 ] || die "filter-repo failed rc=$RC"
say "🟩 filter-repo ok"
say

say "# VERIFY (leak not reachable in history)"
git log --all -- "$LEAK_PATH" >/dev/null 2>&1 && die "leak path still in history after rewrite"
say "🟩 git log does not show leak path"
say

say "# VERIFY (object scan: filename not present)"
git rev-list --objects --all | rg -q "$(basename "$LEAK_PATH")" && die "found filename in object list after rewrite"
say "🟩 object scan clean"
say

say "# ACTION (drop local PR refs; GitHub denies pushing hidden refs)"
if git show-ref --quiet 'refs/pull/*'; then
  git for-each-ref --format='%(refname)' refs/pull/ | while IFS= read -r r; do
    git update-ref -d "$r" || exit 1
  done || die "failed deleting refs/pull/*"
fi
say "🟩 local pull refs deleted (if any)"
say

say "# ACTION (force-push rewritten history: heads + tags only)"
git push --force --all origin || die "push --all failed"
git push --force --tags origin || die "push --tags failed"
say "🟩 push ok"
