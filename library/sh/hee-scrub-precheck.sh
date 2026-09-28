#!/bin/sh
# hee-scrub-precheck.sh
# Purpose: repo-proofed precheck for wrong-repo leak scrub (mirror clone + evidence)
# Usage:
#   hee-scrub-precheck.sh --repo-slug owner/repo --leak-path path/in/repo [--workdir /tmp/x] [--soa ~/.hee/index/_.yaml]
#
# Notes:
# - Anchors to SOA and checks verify_identity_before_emit (or legacy verify_identity_before_writes).
# - Does not rely on PWD.
# - Produces a WORKDIR containing a --mirror clone for APPLY step.

SOA="${HOME}/.hee/index/_.yaml"
REPO_SLUG=""
LEAK_PATH=""
WORKDIR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --soa) SOA="$2"; shift 2 ;;
    --repo-slug) REPO_SLUG="$2"; shift 2 ;;
    --leak-path) LEAK_PATH="$2"; shift 2 ;;
    --workdir) WORKDIR="$2"; shift 2 ;;
    *) echo "🔴 unknown arg: $1"; shift ;;
  esac
done

echo '# STATUS'
echo "🟦 soa=$SOA"
echo "🟦 repo_slug=$REPO_SLUG"
echo "🟦 leak_path=$LEAK_PATH"

test -f "$SOA" && echo "🟩 soa exists" || echo "🔴 soa missing"
command -v git >/dev/null 2>&1 && echo "🟩 git present" || echo "🔴 git missing"
command -v yq  >/dev/null 2>&1 && echo "🟩 yq present"  || echo "🟨 yq missing (invariant check skipped)"

echo
echo '# VERIFY (SOA invariant gate)'
if command -v yq >/dev/null 2>&1 && test -f "$SOA"; then
  yq -r '."yaml.v0".invariants[]' "$SOA" 2>/dev/null | grep -Fx 'verify_identity_before_emit' >/dev/null 2>&1
  INV_EMIT=$?
  yq -r '."yaml.v0".invariants[]' "$SOA" 2>/dev/null | grep -Fx 'verify_identity_before_writes' >/dev/null 2>&1
  INV_WRITE=$?
  if [ "$INV_EMIT" -eq 0 ]; then
    echo "🟩 invariant=verify_identity_before_emit present"
  elif [ "$INV_WRITE" -eq 0 ]; then
    echo "🟨 invariant=verify_identity_before_writes present (migration -> verify_identity_before_emit)"
  else
    echo "🔴 missing invariant gate (need verify_identity_before_emit)"
  fi
else
  echo "🟨 invariant check skipped"
fi

echo
echo '# WORKDIR'
if [ -z "$WORKDIR" ]; then
  WORKDIR="$(mktemp -d)"
fi
MIRROR_DIR="${WORKDIR}/repo.mirror"
echo "🟦 workdir=$WORKDIR"
echo "🟦 mirror=$MIRROR_DIR"

echo
echo '# ACTION (mirror clone)'
git clone --mirror "git@github.com:${REPO_SLUG}.git" "$MIRROR_DIR"
echo "🟦 clone_rc=$?"

echo
echo '# VERIFY (origin matches)'
cd "$MIRROR_DIR" 2>/dev/null || echo "🔴 cd failed"
ORIGIN_URL="$(git remote get-url origin 2>/dev/null)"
echo "🟦 origin=$ORIGIN_URL"
echo "$ORIGIN_URL" | grep -F "$REPO_SLUG" >/dev/null 2>&1 && echo "🟩 origin matches" || echo "🔴 origin mismatch"

echo
echo '# VERIFY (leak presence snapshot)'
git log --all -n 10 --oneline -- "$LEAK_PATH" || true

echo
echo '# NEXT'
echo "🟦 Run APPLY with: --workdir $WORKDIR (same workdir) and same --repo-slug/--leak-path"
