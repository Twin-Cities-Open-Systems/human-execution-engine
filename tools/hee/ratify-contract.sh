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
  if ! grep -q "^status: proposed" "$CONTRACT"; then
    echo "SKIP: $CONTRACT doesn't show 'status: proposed' -- already ratified, or unexpected format. Not touching it." >&2
    skipped+=("$CONTRACT (not status:proposed)")
    continue
  fi

  ASC="${CONTRACT}.asc"
  echo "--- staging $CONTRACT (status -> ratified, evidence field added if applicable) ---"
  sed -i "s/^status: proposed/status: ratified/" "$CONTRACT"
  if grep -q "ratification_required_from:" "$CONTRACT"; then
    sed -i "/ratification_required_from:/a\\  ratification_evidence: \"$(basename "$ASC") -- detached GPG signature, key $KEYID ($SIGNER), covers the exact ratified content in this file\"" "$CONTRACT"
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
