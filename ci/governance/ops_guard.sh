#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

FROZEN=(
  "docs/governance/operations/GOVERNANCE_OPERATIONS.md"
  "docs/governance/operations/GOVERNANCE_VERSIONING.md"
  "docs/governance/operations/GOVERNANCE_CHANGE_PROCESS.md"
)

MANIFEST="docs/governance/operations/INTEGRITY_SHA256SUMS"
CHANGES_DIR="docs/governance/operations/changes"

# SRO approver pattern is org-supplied, never hardcoded here -- HEE
# itself stays human/org-agnostic. Set HEE_SRO_APPROVER_PATTERN in the
# consuming org's CI env (TCOS reads this from
# tcos-audit/policy/approvers.yaml's approved_by_pattern). With nothing
# set, fall back to accepting any named approver rather than baking in
# one specific identity.
SRO_APPROVER_PATTERN="${HEE_SRO_APPROVER_PATTERN:-.+}"

die() { echo "ERROR: $*" >&2; exit 1; }

# Determine diff base
BASE=""
if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
  git fetch --no-tags --depth=1 origin "${GITHUB_BASE_REF}" >/dev/null 2>&1 || true
  BASE="origin/${GITHUB_BASE_REF}"
else
  if git rev-parse HEAD^ >/dev/null 2>&1; then
    BASE="HEAD^"
  else
    BASE="HEAD"
  fi
fi

CHANGED="$(git diff --name-only "${BASE}...HEAD" || true)"

[[ -f "$MANIFEST" ]] || die "Missing $MANIFEST. Create it and commit it."

# Validate sha256 manifest (ignore comment/blank lines)
NONCOMMENT="$(grep -vE '^\s*(#|$)' "$MANIFEST" || true)"
if [[ -n "$NONCOMMENT" ]]; then
  if ! (printf "%s\n" "$NONCOMMENT" | sha256sum -c - >/dev/null 2>&1); then
    die "Integrity check failed. $MANIFEST does not match current frozen artifacts."
  fi
fi

# Detect frozen changes
FROZEN_TOUCHED=0
for f in "${FROZEN[@]}"; do
  if echo "$CHANGED" | grep -qx "$f"; then
    FROZEN_TOUCHED=1
    break
  fi
done

if [[ "$FROZEN_TOUCHED" -eq 1 ]]; then
  if ! echo "$CHANGED" | grep -Eq "^${CHANGES_DIR}/.+\.md$"; then
    die "Frozen governance ops artifacts changed. Add a change record under ${CHANGES_DIR}/ (see GOVERNANCE_CHANGE_PROCESS.md)."
  fi

  if ! echo "$CHANGED" | grep -qx "$MANIFEST"; then
    die "Frozen governance ops artifacts changed. Update ${MANIFEST}."
  fi

  TOUCHED_RECORDS="$(echo "$CHANGED" | grep -E "^${CHANGES_DIR}/.+\.md$" || true)"
  while IFS= read -r rec; do
    [[ -n "$rec" ]] || continue
    [[ -f "$rec" ]] || continue
    grep -qE '^## Trigger' "$rec" || die "Change record $rec missing '## Trigger'."
    grep -qE '^## Evidence' "$rec" || die "Change record $rec missing '## Evidence'."
    grep -qE "Approved-by:\s*${SRO_APPROVER_PATTERN}" "$rec" || die "Change record $rec missing SRO approval line."
  done <<< "$TOUCHED_RECORDS"
fi

echo "OK: governance operations guardrails passed."
