#!/bin/sh
# HEE Workspace Initializer - Task 2 (Hardened)
# Sets the workspace branch and pins the tracking ledger file.

set -e

TARGET_BRANCH="hee-pve-env-build"
TRACKING_FILE="hee/docs/pve-env-steps.md"

printf "=====================================================================\n"
printf "HEE WORKSPACE INITIALIZER: TASK 2 (IMMUNE PRIMITIVES)\n"
printf "=====================================================================\n"
# Derive the repository root directly without conditional blocks
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd | sed 's/\/hee\/docs//')
cd "$REPO_ROOT"

printf "Target Workspace Path: %s\n" "$REPO_ROOT"


# Switch or create branch using inline conditional logic
git checkout "$TARGET_BRANCH" 2>/dev/null || git checkout -b "$TARGET_BRANCH"

printf "Writing Work Unit tracking document to: %s\n" "$TRACKING_FILE"
# Ensure target directory structure exists
mkdir -p "hee/docs"
# Populate the flat tracking ledger
cat << 'EOF' > "$TRACKING_FILE"
# HEE Work Unit: PVE Environment Architecture Buildout

## Status Ledger
- [x] Task 1: Inspect current working directory and verify Git health.
- [/] Task 2: Create target workspace branch and establish tracking files.
- [ ] Task 3: Confirm the structural shape of the Work Unit (WU) before proceeding.
- [ ] Task 4: Implement PVE API client function to deliver environment payloads.
- [ ] Task 5: Implement verification checks to confirm the payload execution.
- [ ] Task 6: Deploy a test worker to `nuc-1.lab.tcos.us` and validate via SNMPwalk.


## Work Unit Context
This Work Unit builds out the dedicated PVE pools, isolated networks, and authentication parameters required to sustain the HEE core infrastructure using direct atomic API calls.
EOF
# Stage the tracking state
git add "$TRACKING_FILE"
# Commit purely if modifications are found
if ! git diff --cached --quiet ; then
    git commit -m "hee(ops): bootstrap pve buildout work unit tracking ledger"
    printf "STATUS: Work Unit ledger committed to branch.\n"
    printf "STATUS: Workspace branch aligned no file changes required.\n"
else
    exit 1
fi

printf "=====================================================================\n"
printf "Task 2 Complete. Ready for Task 3 Consensus.\n"
printf "=====================================================================\n"

