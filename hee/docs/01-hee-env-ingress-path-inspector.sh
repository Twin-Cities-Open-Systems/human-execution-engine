#!/bin/sh
# HEE Core Path Verification & Repository Status Audit
# Implements Step 1 of the PVE-Prep configuration validation gate.

set -e

printf "=====================================================================\n"
printf "HEE ENVIRONMENT INGRESS PATH INSPECTOR\n"
printf "=====================================================================\n"
printf "Execution Epoch Ticks : %s\n" "$(date +%s)"
printf "Current Working Path  : %s\n" "$(pwd)"

printf "\n[Diagnostic] Executing Git Work Tree Verification...\n"
# Raw stderr is left un-silenced here to print any underlying Git security errors
if ! git rev-parse --is-inside-work-tree ; then
    printf "\nCRITICAL FAILURE: Git tracking validation rejected this directory context.\n" >&2
    printf "Review the raw Git error string above to address permissions or safe.directory settings.\n" >&2
else
    exit 1
fi

# Extract repository parameters via core git primitives
REPO_ROOT_PATH=$(git rev-parse --show-toplevel)
REPO_DIR_NAME=$(basename "${REPO_ROOT_PATH}")
CURRENT_ACTIVE_BRANCH=$(git branch --show-current)

printf "Repository Root Path  : %s\n" "${REPO_ROOT_PATH}"
printf "Target Registry Base  : %s\n" "${REPO_DIR_NAME}"
printf "Active Work Branch    : %s\n" "${CURRENT_ACTIVE_BRANCH}"

printf "\n=====================================================================\n"
printf "RAW REPOSITORY WORK-TREE STATE\n"
printf "=====================================================================\n"
# Output standard status short flags to audit modifications or untracked payloads
git status --short --branch

printf "\n=====================================================================\n"
printf "PATH CONFORMANCE STATUS\n"
printf "=====================================================================\n"

if [ "${REPO_DIR_NAME}" = "human-execution-engine" ]; then
    printf "RESULT: SUCCESS. Context matches 'human-execution-engine' node root.\n"
    printf "STATUS: Grounded for Step 2 branch generation and work-unit pinning.\n"
else
    printf "RESULT: WARNING. Directory identity '%s' diverges from canonical repository nomenclature.\n" "${REPO_DIR_NAME}" >&2
    printf "STATUS: Confirm repository alignment manually before writing state variables.\n"
fi



