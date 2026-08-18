#!/usr/bin/env bash
set -euo pipefail

# CI enforcement:
# - required files exist
# - prompts reference scripts/hee_git_ops.sh
# - runbook exists
# - CI workflow includes enforcement step
# - YAML path header naming enforcement
#
# This script should be invoked by .github/workflows/ci.yaml.

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

req_files=(
  "docs/guides/GIT_GH_WORKFLOW.md"
  "scripts/hee_git_ops.sh"
  "scripts/hee_ci_gitops_enforce.sh"
  ".github/workflows/ci.yaml"
)

for f in "${req_files[@]}"; do
  [[ -f "$f" ]] || fail "Missing required file: $f"
done

# Ensure scripts are at least parseable and have strict mode.
grep -q "set -euo pipefail" scripts/hee_git_ops.sh || fail "hee_git_ops.sh must use 'set -euo pipefail'"
grep -q "set -euo pipefail" scripts/hee_ci_gitops_enforce.sh || fail "hee_ci_gitops_enforce.sh must use 'set -euo pipefail'"

# Prompts must reference the guarded script.
prompt_files=(
  "prompts/INIT.md"
  "prompts/PROMPTING_RULES.md"
  "prompts/AGENT_STATE_HANDOFF.md"
)

missing_prompt=0
for p in "${prompt_files[@]}"; do
  if [[ ! -f "$p" ]]; then
    printf 'WARN: Prompt file missing (expected by policy): %s\n' "$p" >&2
    missing_prompt=1
  fi
done

if [[ "$missing_prompt" -eq 1 ]]; then
  fail "One or more required prompt files are missing. Expected: ${prompt_files[*]}"
fi

for p in "${prompt_files[@]}"; do
  grep -q "scripts/hee_git_ops.sh" "$p" || fail "Prompt must reference scripts/hee_git_ops.sh: $p"
  grep -q "BLOCKER" "$p" || fail "Prompt must include BLOCKER semantics: $p"
done

# CI workflow must call this enforcement script.
grep -q "scripts/hee_ci_gitops_enforce.sh" .github/workflows/ci.yaml \
  || fail "ci.yml must run scripts/hee_ci_gitops_enforce.sh"

# Enforce YAML path header naming compliance
echo "🔍 Checking YAML path header naming compliance..."
if [ -f "ci/naming/fix_yaml_path_header.py" ]; then
  echo "✅ YAML path header script found"
  # Run the naming check in check mode
  if ! python3 ci/naming/fix_yaml_path_header.py --check; then
    fail "YAML path header naming compliance check failed"
  fi
  echo "✅ YAML path header naming compliance check passed"
else
  fail "YAML path header script not found at ci/naming/fix_yaml_path_header.py"
fi

# Enforce authoritative YAML naming rules
echo "🔍 Checking authoritative YAML naming rules..."
if [ -f "ci/naming/check_authoritative_yaml_naming.py" ]; then
  echo "✅ Authoritative YAML naming checker found"
  # Run the naming check
  if ! python3 ci/naming/check_authoritative_yaml_naming.py --repo-root . --scope contracts --scope blueprints; then
    fail "Authoritative YAML naming rules check failed"
  fi
  echo "✅ Authoritative YAML naming rules check passed"
else
  fail "Authoritative YAML naming checker not found at ci/naming/check_authoritative_yaml_naming.py"
fi

# Optional: doc-path alignment guardrail (presence check, not correctness of content)
# We only enforce that the workflow is no longer hard-coded to legacy docs/*.md.
if grep -qE "(^|[^/])docs/\*\.md" .github/workflows/ci.yaml; then
  fail "ci.yml still references legacy 'docs/*.md' glob; update to docs/doctrine/* and docs/specs/* (and/or docs/guides/*)."
fi

printf "OK: HEE GitOps admission control enforcement checks passed.\n"
