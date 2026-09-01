# shfn.birth.verify.shfn.bash
# Guard: shfn births must land in tools/shellboss/library/bash in the same PR,
# and must include wiring in install.sh + shellboss.

# Usage:
#   . tools/shellboss/library/bash/shfn.birth.verify.shfn.bash
#   shfn_birth_verify
#
# Prints PASS/FAIL summary and writes a mktemp report path.

shfn_birth_verify() {
  local OUT
  OUT="$(mktemp -t hee.shfn.birth.verify.XXXXXX.txt)" || return 1
  ln -sf "$OUT" /tmp/hee.shfn.birth.verify.latest.txt 2>/dev/null || true

  # Derived from this file's own location, never a hardcoded home. Rule 10:
  # a real user's home path in a shared script breaks for every other user,
  # and this repo is checked out per-user (/home/spencer and /home/claude both
  # exist on kiosk, each 0750 and unreadable by the other). Same principle the
  # hee router uses -- TOOL root comes from the script location.
  local repo
  repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)" || return 1
  cd "$repo" || { echo "❌ ERROR: cd failed: $repo"; return 1; }

  # Diff range: prefer merge-base with origin/main when available; fallback to HEAD~1.
  local base
  base="$(git merge-base origin/main HEAD 2>/dev/null)" || base=""
  if [ -z "$base" ]; then
    base="HEAD~1"
  fi

  {
    echo "# shfn.birth.verify"
    echo "timestamp=$(date -Is)"
    echo "range=$base..HEAD"
    echo
    git diff --name-status "$base..HEAD" || true
    echo
  } > "$OUT"

  # New/modified shfn files in this change range
  local shfns
  shfns="$(git diff --name-only "$base..HEAD" | rg '\.shfn\.bash$' 2>/dev/null || true)"

  if [ -z "$shfns" ]; then
    echo "✅ SHFN-BIRTH verify: no shfn changes"
    echo "🧾 REPORT $OUT"
    return 0
  fi

  # Enforce canonical location for any shfn touched
  local bad_path=0
  while IFS= read -r f; do
    if [ -z "$f" ]; then continue; fi
    case "$f" in
      tools/shellboss/library/bash/*) : ;;
      *) bad_path=1 ;;
    esac
  done <<EOF_LIST
$shfns
EOF_LIST

  # Enforce wiring touched when shfn changes exist
  local w_install=0 w_shellboss=0
  git diff --name-only "$base..HEAD" | rg -q '^tools/shellboss/install\.sh$' && w_install=1 || true
  git diff --name-only "$base..HEAD" | rg -q '^tools/shellboss/shellboss$' && w_shellboss=1 || true

  {
    echo "# shfn files"
    echo "$shfns"
    echo
    echo "# checks"
    echo "canonical_path_ok=$((1-bad_path))"
    echo "install_wired=$w_install"
    echo "shellboss_wired=$w_shellboss"
    echo
  } >> "$OUT"

  if [ "$bad_path" -ne 0 ] || [ "$w_install" -ne 1 ] || [ "$w_shellboss" -ne 1 ]; then
    echo "🛑 SHFN-BIRTH verify: FAIL"
    echo "📌 canonical_path_ok=$((1-bad_path)) install_wired=$w_install shellboss_wired=$w_shellboss"
    echo "🧾 REPORT $OUT"
    return 1
  fi

  echo "✅ SHFN-BIRTH verify: PASS"
  echo "📌 canonical_path_ok=1 install_wired=1 shellboss_wired=1"
  echo "🧾 REPORT $OUT"
  return 0
}
