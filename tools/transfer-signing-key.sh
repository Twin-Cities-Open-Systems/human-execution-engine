#!/usr/bin/env bash
# path: tools/transfer-signing-key.sh
# Move a GPG secret key directly between two hosts over SSH, so it never
# gets hand-typed, hand-copied, or committed anywhere -- secret key
# material must never touch git (see hee.fleet-hosts.contract.v1.yaml
# for verified host IPs/FQDNs this script reads instead of hardcoding).
#
# This script is meant to be run FROM the host that already holds the
# key (the source), pushing it TO the destination host over SSH. It
# never writes the key to disk in this repo or anywhere persistent --
# only through an SSH pipe, gpg->gpg.
#
# Usage (run this ON the source host, e.g. nuc-1):
#   tools/transfer-signing-key.sh [-y|--yes] <key-id> <dest-ssh-host>
#
# Interactive by default (this moves secret key material -- worth a real
# confirm), but -y/--yes skips the prompt for scripted/cron use, per
# CRON-REAL-1 in blueprints/spec-hee-cron-tooling-blueprint.yaml
# (non-interactive, no TTY required).
#
# Example (Spencer, on nuc-1, sending his key to kiosk):
#   tools/transfer-signing-key.sh inspector@tcos.us kiosk.lab.tcos.us
set -euo pipefail

assume_yes=0
if [[ "${1:-}" == "-y" || "${1:-}" == "--yes" ]]; then
  assume_yes=1
  shift
fi

key_id="${1:?usage: transfer-signing-key.sh [-y|--yes] <key-id> <dest-ssh-host>}"
dest_host="${2:?usage: transfer-signing-key.sh [-y|--yes] <key-id> <dest-ssh-host>}"

if ! gpg --list-secret-keys "$key_id" >/dev/null 2>&1; then
  echo "ERROR: no secret key for '$key_id' in the keyring on $(hostname) -- this must run on the host that HAS the key." >&2
  exit 1
fi

if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$dest_host" true 2>/dev/null; then
  echo "ERROR: can't reach $dest_host over SSH from $(hostname). Check the host is up and your key is authorized there." >&2
  exit 1
fi

if [[ "$assume_yes" -ne 1 ]]; then
  echo "About to pipe the SECRET key for '$key_id' from $(hostname) to $dest_host over SSH."
  echo "This does not touch disk on either end outside each host's own gnupg keyring, and never touches git."
  read -r -p "Continue? [y/N] " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

gpg --export-secret-keys --armor "$key_id" | ssh "$dest_host" gpg --import

echo
echo "OK: key imported on $dest_host. Verifying it landed:"
ssh "$dest_host" gpg --list-secret-keys "$key_id"
echo
echo "Now BOTH hosts hold this secret key. If that's not what you want long-term,"
echo "revoke/remove it from whichever host shouldn't keep it: gpg --delete-secret-keys <key-id>"
