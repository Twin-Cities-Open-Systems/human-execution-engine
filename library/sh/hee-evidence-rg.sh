#!/bin/sh
# hee-evidence-rg.sh — ripgrep inside the repo evidence corpus (read-only helper)
#
# usage:
#   hee-evidence-rg.sh <repo_root> <pattern> [rg args...]
#
# examples:
#   ./library/sh/hee-evidence-rg.sh . "home occupation"
#   ./library/sh/hee-evidence-rg.sh . "minneapolis" -i

repo=${1:-}
pat=${2:-}

if [ -z "$repo" ] || [ -z "$pat" ]; then
  echo "usage: $(basename "$0") <repo_root> <pattern> [rg args...]" >&2
  exit 2
fi
shift 2

if ! command -v rg >/dev/null 2>&1; then
  echo "error: rg (ripgrep) not found on PATH" >&2
  exit 127
fi

# evidence root auto-detect
ev=""
if [ -d "$repo/hee/evidence/src" ]; then
  ev="$repo/hee/evidence/src"
elif [ -d "$repo/hee/evidence" ]; then
  ev="$repo/hee/evidence"
else
  echo "error: evidence root not found under $repo/hee/evidence/src or $repo/hee/evidence" >&2
  exit 2
fi

# NOTE:
# - exclude any nested .git dirs (Codex P2)
# - use -e for pattern so leading '-' can't be parsed as flags (Codex P2)
# - "$@" are extra rg args (now correctly positioned before pattern)
rg --color=never -n --no-heading --hidden \
  --glob '!**/.git/**' \
  --glob '!**/node_modules/**' \
  "$@" \
  -e "$pat" \
  "$ev"
rc=$?

case "$rc" in
  0) exit 0 ;;
  1) echo "no matches: $pat" >&2; exit 0 ;;
  *) exit "$rc" ;;
esac
