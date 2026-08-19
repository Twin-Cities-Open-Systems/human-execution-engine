#!/usr/bin/env bash
# ratify-contract.sh -- correct-order contract ratification.
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
# Usage: ./ratify-contract.sh <path-to-contract.yaml> <gpg-key-id> <signer-name>
set -euo pipefail

CONTRACT="${1:?usage: $0 <contract.yaml> <gpg-key-id> <signer-name>}"
KEYID="${2:?usage: $0 <contract.yaml> <gpg-key-id> <signer-name>}"
SIGNER="${3:?usage: $0 <contract.yaml> <gpg-key-id> <signer-name>}"

if [ ! -f "$CONTRACT" ]; then
  echo "ERROR: $CONTRACT not found" >&2
  exit 1
fi

if ! grep -q "status: proposed" "$CONTRACT"; then
  echo "ERROR: $CONTRACT doesn't show 'status: proposed' -- already ratified, or unexpected format. Not touching it." >&2
  exit 1
fi

ASC="${CONTRACT}.asc"

echo "--- 1. staging final content (status -> ratified, evidence field added) ---"
sed -i "s/status: proposed/status: ratified/" "$CONTRACT"
# Insert evidence line right after ratification_required_from, generic
# reference only -- no signature-specific bytes, so this can exist
# BEFORE the actual signature is made.
if grep -q "ratification_required_from:" "$CONTRACT"; then
  sed -i "/ratification_required_from:/a\\  ratification_evidence: \"$(basename "$ASC") -- detached GPG signature, key $KEYID ($SIGNER), covers the exact ratified content in this file\"" "$CONTRACT"
fi

echo "--- 2. this is the FINAL content -- sign it now ---"
echo "Run this yourself (needs your own secret key):"
echo "  gpg --detach-sign --armor '$CONTRACT'"
echo
echo "Once '$ASC' exists next to it, commit both files together."
echo "Do NOT edit '$CONTRACT' again after signing -- any further edit invalidates the signature, same bug this script exists to prevent."
