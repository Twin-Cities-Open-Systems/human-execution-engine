#!/usr/bin/env bash
# ratify-contract.sh -- correct-order contract ratification, real batch
# support (extended 2026-08-25, same real ask as hee-exif's bulk
# gpg-sign: "promote and sign all the outstanding contracts").
#
# The bug this fixes: signing a contract, THEN editing status/evidence
# fields afterward, invalidates the signature (it no longer matches
# the committed bytes). Correct order: stage the FINAL content
# (status: ratified + evidence field already in place, since the
# evidence field only needs to reference a filename convention, not
# the actual signature bytes) -- THEN sign that final version.
#
# Run from inside a human-execution-engine checkout, on the branch
# you want to commit the ratification to.
#
# Usage: ./ratify-contract.sh --key <gpg-key-id> --signer <name> <contract.yaml> [<contract2.yaml> ...]
set -euo pipefail

KEYID=""
SIGNER=""
CONTRACTS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --key) KEYID="$2"; shift 2 ;;
    --signer) SIGNER="$2"; shift 2 ;;
    *) CONTRACTS+=("$1"); shift ;;
  esac
done

if [ -z "$KEYID" ] || [ -z "$SIGNER" ] || [ "${#CONTRACTS[@]}" -eq 0 ]; then
  echo "usage: $0 --key <gpg-key-id> --signer <name> <contract.yaml> [<contract2.yaml> ...]" >&2
  exit 1
fi

staged=()
skipped=()

for CONTRACT in "${CONTRACTS[@]}"; do
  if [ ! -f "$CONTRACT" ]; then
    echo "ERROR: $CONTRACT not found -- skipping" >&2
    skipped+=("$CONTRACT (not found)")
    continue
  fi
  # Match `status: proposed` at ANY indent. It was anchored to column 0 and
  # every real HEE object nests it under `spec:` -- so this grep matched
  # NOTHING, ever, and the script reported success having touched no file.
  # Measured 2026-09-09 across every contract and registry in both repos:
  # zero at column 0. A ratification tool that ratifies nothing is worse than
  # no tool, because "staged 0, skipped 1" reads as "already done".
  if ! grep -qE "^[[:space:]]*status: proposed" "$CONTRACT"; then
    echo "SKIP: $CONTRACT doesn't show 'status: proposed' -- already ratified, or unexpected format. Not touching it." >&2
    skipped+=("$CONTRACT (not status:proposed)")
    continue
  fi

  ASC="${CONTRACT}.asc"
  echo "--- staging $CONTRACT (status -> ratified, evidence field added if applicable) ---"
  sed -i -E "s/^([[:space:]]*)status: proposed/\\1status: ratified/" "$CONTRACT"
  EV="$(basename "$ASC") -- detached GPG signature, key $KEYID ($SIGNER), covers the exact ratified content in this file"
  if grep -qE "^[[:space:]]*ratification_evidence:" "$CONTRACT"; then
    # REPLACE, never append. Measured 2026-09-09: appending produced two keys
    # at the same level, with the contract's own "PENDING -- not yet ratified"
    # line immediately after the inserted one. YAML takes the LAST duplicate,
    # so the real evidence was silently overridden by the placeholder it was
    # meant to replace -- a ratified contract still declaring itself
    # unratified, and parsing cleanly while it did.
    sed -i -E "s|^([[:space:]]*)ratification_evidence:.*|\\1ratification_evidence: \"$EV\"|" "$CONTRACT"
  elif grep -q "ratification_required_from:" "$CONTRACT"; then
    IND=$(grep -oE "^[[:space:]]*ratification_required_from:" "$CONTRACT" | head -1 | sed -E "s/ratification_required_from://")
    sed -i "/ratification_required_from:/a\\${IND}ratification_evidence: \"$EV\"" "$CONTRACT"
  fi
  staged+=("$CONTRACT")
done

echo
echo "=== staged ${#staged[@]}, skipped ${#skipped[@]} ==="
if [ "${#skipped[@]}" -gt 0 ]; then
  printf 'skipped: %s\n' "${skipped[@]}"
fi

if [ "${#staged[@]}" -eq 0 ]; then
  echo "nothing to sign."
  exit 0
fi

echo
echo "This is the FINAL content for each -- sign them now yourself (needs your own secret key)."
echo "Run each of these:"
for CONTRACT in "${staged[@]}"; do
  echo "  gpg --detach-sign --armor '$CONTRACT'"
done
echo
echo "Once each .asc exists next to its contract, commit contract+asc pairs together."
echo "Do NOT edit any contract again after signing it -- any further edit invalidates that one signature, same bug this script exists to prevent."
