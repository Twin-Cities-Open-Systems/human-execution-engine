#!/usr/bin/env bash
# path: tools/sign-card.sh
# Sign one pending attestor slot in a HEE Card (spec.attestation.<name>
# with a "status: pending" field -- see hee/cards/*.card.v1.yaml), then
# verify everything landed correctly. Real fix for the 2026-08-18
# failure mode: hand-copying a multi-line gpg command out of a YAML
# note: field (the embedded newline pastes as literal "\n" text) and
# guessing which "yq" is on PATH (see HEE#240 -- Debian ships
# kislyuk/python-yq under the same binary name as mikefarah/yq; this
# script refuses to run under the wrong one rather than silently
# misbehaving).
#
# Usage:
#   tools/sign-card.sh <card-file> <attestor-name> <gpg-key-id>
#
# Example (Spencer, on nuc-1, where his secret key actually lives):
#   tools/sign-card.sh hee/cards/spencer-blank-generation-lyric.card.v1.yaml spencer inspector@tcos.us
set -euo pipefail

card_file="${1:?usage: sign-card.sh <card-file> <attestor-name> <gpg-key-id>}"
attestor="${2:?usage: sign-card.sh <card-file> <attestor-name> <gpg-key-id>}"
key_id="${3:?usage: sign-card.sh <card-file> <attestor-name> <gpg-key-id>}"

if ! yq --version 2>/dev/null | grep -qi mikefarah; then
  echo "ERROR: this needs mikefarah/yq; '$(command -v yq)' is a different tool with the same name." >&2
  echo "       see https://github.com/Twin-Cities-Open-Systems/human-execution-engine/issues/240" >&2
  exit 1
fi

if [[ ! -f "$card_file" ]]; then
  echo "ERROR: $card_file not found" >&2
  exit 1
fi

if ! gpg --list-secret-keys "$key_id" >/dev/null 2>&1; then
  echo "ERROR: no secret key for '$key_id' in the keyring on $(hostname)." >&2
  echo "       run this on whichever host actually holds that key." >&2
  exit 1
fi

path=".spec.attestation.${attestor}"
if [[ "$(yq eval "${path} | has(\"status\")" "$card_file")" != "true" ]]; then
  echo "ERROR: ${path}.status not found in $card_file -- wrong attestor name, or this slot isn't the pending-status shape this script expects." >&2
  exit 1
fi

current_status="$(yq eval "${path}.status" "$card_file")"
if [[ "$current_status" != "pending" ]]; then
  echo "ERROR: ${path}.status is '${current_status}', not 'pending' -- already signed, or something else is going on. Not touching it." >&2
  exit 1
fi

sig_file="${card_file}.${attestor}.asc"
ts="$(date -Is)"

# Snapshot every field outside this attestor's status/signed_artifact/signed_at
# so we can prove nothing else in the document moved.
before_json="$(yq -o=json eval "del(${path}.status, ${path}.signed_artifact, ${path}.signed_at)" "$card_file")"

# One atomic pass, not three sequential ones -- yq re-serializes the
# whole file on every -i call, and chaining separate calls was
# observed (2026-08-18) to multiply a folded-scalar blank-line paragraph
# break elsewhere in the document on each pass.
yq -i "${path}.status = \"signed\" | ${path}.signed_artifact = \"$(basename "$sig_file") (detached sig, this commit)\" | ${path}.signed_at = \"${ts}\"" "$card_file"

after_json="$(yq -o=json eval "del(${path}.status, ${path}.signed_artifact, ${path}.signed_at)" "$card_file")"

if [[ "$before_json" != "$after_json" ]]; then
  echo "ERROR: fields outside ${path}.{status,signed_artifact,signed_at} changed -- aborting. Restore $card_file from git before retrying." >&2
  diff <(echo "$before_json") <(echo "$after_json") >&2 || true
  exit 1
fi

gpg --batch --yes --armor --local-user "$key_id" --detach-sign --output "$sig_file" "$card_file"
gpg --no-tty --batch --verify "$sig_file" "$card_file"

echo
echo "OK: ${attestor} signed and verified against the final file."
echo "    file:      $card_file"
echo "    signature: $sig_file"
echo
echo "Next: git add '$card_file' '$sig_file' && git commit && git push"
