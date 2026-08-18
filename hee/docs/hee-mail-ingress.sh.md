# Thesis

deliver mail, not compute

## hee-mail-ingress.sh

```bash
#!/bin/bash

# ==============================================================================
# HEE Architecture: Minimalist MTA Command Ingress Script# Purpose: Processes incoming PGP-signed mail packets via standard input (MTA pipe),#          verifies cryptographic signatures, and updates the local SNMP MIB state.# Architecture Branch: Machine Rights Org / Fleet Ops Intersection# Ethos: Bypasses bloated HTTP webhooks and user-space messaging queues.
# ==============================================================================

set -euo pipefail
# --- Configuration Variables ---# Path to the isolated GPG home directory containing verified corporate public keys
GNUPGHOME="/etc/hee/gpg"
export GNUPGHOME
# The base Object Identifier (OID) assigned to your Private Enterprise Number (PEN)# Matches the custom schema compiled inside the HEE-ROOT-MIB definition
BASE_OID="1.3.6.1.4.1.55555"

CONTRACT_STATUS_SUB_ARC="3.2.1.6" # .machineRightsOrg.agentContracts.contractTable.contractEntry.contractStatus
# Target SNMP daemon loop settings
SNMP_HOST="127.0.0.1"
SNMP_COMMUNITY="private" # Write community string mapped in your local snmpd.conf
# Temporary file storage allocations
RAW_MAIL=$(mktemp /tmp/hee_mail.XXXXXX)
DECRYPTED_PAYLOAD=$(mktemp /tmp/hee_payload.XXXXXX)
GPG_STATUS=$(mktemp /tmp/hee_gpg_status.XXXXXX)
# Ensure automatic cleanup of temporary file descriptors on termination or failure
trap 'rm -f "$RAW_MAIL" "$DECRYPTED_PAYLOAD" "$GPG_STATUS"' EXIT
# --- Step 1: Read Email from Standard Input (MTA Pipeline) ---# Postfix aliases or standard mail transfer loops pass raw MIME blocks directly via stdin
cat > "$RAW_MAIL"
# --- Step 2: Extract ASCII-Armored PGP Text Block ---

# Isolates the signed payload boundaries from mail headers and raw MIME multi-part structuresif ! sed -n '/^-----BEGIN PGP SIGNED MESSAGE-----/,/^-----END PGP SIGNATURE-----/p' "$RAW_MAIL" > "$DECRYPTED_PAYLOAD"; then
    echo "FAIL: No valid PGP signed message boundaries found in incoming mail stream." >&2
    exit 1fi
# Assert the file contains real data bytes before proceeding to the cryptographic layerif [ ! -s "$DECRYPTED_PAYLOAD" ]; then
    echo "FAIL: Extracted PGP payload file descriptor is completely empty." >&2
    exit 1fi
# --- Step 3: Verify Cryptographic Signatures and Extract Identity ---# --status-file writes clean, machine-parseable status tokens to a dedicated descriptor# --verify validates the data block parameters without forcing explicit clear-text output decryptionif ! gpg --homedir "$GNUPGHOME" --status-file "$GPG_STATUS" --verify "$DECRYPTED_PAYLOAD" >/dev/null 2>&1; then
    echo "FAIL: GPG signature verification routine crashed or execution failed." >&2
    exit 2fi

# Parse status file for the absolute VALIDSIG indicator# VALIDSIG format: [VALIDSIG fingerprint date timestamp ...]if ! grep -q "^\[GNUPG:\] VALIDSIG" "$GPG_STATUS"; then
    echo "SECURITY ALERT: Unsigned or untrusted command packet discarded. Signature validation failed." >&2
    exit 3fi
# Extract the full 40-character hexadecimal GPG fingerprint of the identity signing key
SIGNER_FINGERPRINT=$(awk '/^\[GNUPG:\] VALIDSIG/ {print $3}' "$GPG_STATUS")
# --- Step 4: Verify Senior Authority Standing ---# Validate the extracted signer fingerprint against your local, root-protected manifest list
AUTHORIZED_SIGNERS_FILE="/etc/hee/authorized_senior_signers.list"if [ ! -f "$AUTHORIZED_SIGNERS_FILE" ] || ! grep -Fq "$SIGNER_FINGERPRINT" "$AUTHORIZED_SIGNERS_FILE"; then
    echo "SECURITY ALERT: Fingerprint $SIGNER_FINGERPRINT is cryptographically valid but lacks operational clearance." >&2
    exit 4fi
# --- Step 5: Low-Abstraction Parsing of the Extracted YAML Prose ---

# Extracts operational variables using core text processing primitives without heavy script runtimes# Looks specifically for 'target_contract_index:' and 'action_status_integer:' keys
TARGET_INDEX=$(awk -F': ' '/target_contract_index/ {gsub(/[^0-9]/,"",$2); print $2}' "$DECRYPTED_PAYLOAD")
ACTION_STATUS=$(awk -F': ' '/action_status_integer/ {gsub(/[^0-9]/,"",$2); print $2}' "$DECRYPTED_PAYLOAD")
if [ -z "$TARGET_INDEX" ] || [ -z "$ACTION_STATUS" ]; then
    echo "FAIL: Could not extract integer state variables from YAML message definition block." >&2
    exit 5fi
# Enforce explicit parameter limits matching the compiled HEE ASN.1 boundary parameters# contractStatus syntax maps: active(1), expired(2), revoked(3), compromised(4)if [ "$ACTION_STATUS" -lt 1 ] || [ "$ACTION_STATUS" -gt 4 ]; then
    echo "FAIL: Requested state shift integer ($ACTION_STATUS) violates ASN.1 model constraints." >&2
    exit 6fi
# --- Step 6: Trigger Localized SNMP State Change (The Gate) ---# Assemble the final precise OID path targeting the specific indexed row in the contract table

# Output path pattern: BASE_OID.SUB_ARC.TARGET_INDEX
FINAL_OID="${BASE_OID}.${CONTRACT_STATUS_SUB_ARC}.${TARGET_INDEX}"

echo "INTEGRITY CHECK PASSED: Processing structural command execution state."
echo "Verified Authority Signer: $SIGNER_FINGERPRINT"
echo "Target MIB Address: $FINAL_OID"
echo "Updating State Token to: $ACTION_STATUS"
# Dispatch the low-overhead UDP primitive set operation to lock/unlock the local runtime nodeif ! snmpset -v 2c -c "$SNMP_COMMUNITY" "$SNMP_HOST" "$FINAL_OID" i "$ACTION_STATUS" > /dev/null; then
    echo "FAIL: Core socket delivery fault. snmpset failed to mutate state on local runtime engine." >&2
    exit 7fi

echo "TRANSACTION RECORDED: State synchronization complete."
```

