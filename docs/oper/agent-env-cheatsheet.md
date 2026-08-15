# Agent Environment Cheatsheet

Environment variables and runtime controls for HEE-style agent runs.

## Environment Variables

### Repo Root Binding / Path Safety

```bash
# Operate from repo root; no absolute path writes outside repo
HEE_REPO_ROOT="/path/to/repo"
HEE_WORKING_DIR="${HEE_REPO_ROOT}"
HEE_SAFE_PATHS="${HEE_REPO_ROOT}/doc/oper/**"
```

### Step Variables

```bash
# Per-step identifiers and names
HEE_STEP_ID="step-001"
HEE_STEP_NAME="create-readme"
HEE_RUN_ID="run-$(date +%Y%m%d-%H%M%S)"
HEE_BRANCH="phase/ops-hee-oper-runtime-docs"
```

### Logging Controls

```bash
# Log directory and artifact paths
HEE_LOG_DIR="${HEE_REPO_ROOT}/.hee/logs"
HEE_ARTIFACT_DIR="${HEE_REPO_ROOT}/.hee/artifacts"
HEE_SUMMARY_PATH="${HEE_LOG_DIR}/run-summary.md"
HEE_REPORT_PATH="${HEE_LOG_DIR}/run-report.md"
```

### Mode Controls

```bash
# PLAN vs ACT indicator
HEE_MODE="ACT"  # or "PLAN"
HEE_PLAN_ONLY="false"  # true for PLAN mode
```

## Minimum Required Environment

```bash
export HEE_REPO_ROOT="/home/<user>/git/human-execution-engine"
export HEE_WORKING_DIR="${HEE_REPO_ROOT}"
export HEE_MODE="ACT"
export HEE_STEP_ID="step-$(date +%s)"
export HEE_RUN_ID="run-$(date +%Y%m%d-%H%M%S)"
```

## Recommended Environment

```bash
# Core environment
export HEE_REPO_ROOT="/home/<user>/git/human-execution-engine"
export HEE_WORKING_DIR="${HEE_REPO_ROOT}"
export HEE_MODE="ACT"
export HEE_STEP_ID="step-$(date +%s)"
export HEE_RUN_ID="run-$(date +%Y%m%d-%H%M%S)"
export HEE_BRANCH="phase/ops-hee-oper-runtime-docs"

# Logging
export HEE_LOG_DIR="${HEE_REPO_ROOT}/.hee/logs"
export HEE_ARTIFACT_DIR="${HEE_REPO_ROOT}/.hee/artifacts"
export HEE_SUMMARY_PATH="${HEE_LOG_DIR}/run-summary.md"
export HEE_REPORT_PATH="${HEE_LOG_DIR}/run-report.md"

# Safety
export HEE_SAFE_PATHS="${HEE_REPO_ROOT}/doc/oper/**"
export HEE_PLAN_ONLY="false"
```

## Usage Examples

### Initialize Environment

```bash
# Source this in your shell before running HEE operations
source "${HEE_REPO_ROOT}/doc/oper/agent-env-cheatsheet.md"
```

### Check Environment Status

```bash
echo "HEE Mode: ${HEE_MODE}"
echo "Working Directory: ${HEE_WORKING_DIR}"
echo "Run ID: ${HEE_RUN_ID}"
echo "Branch: ${HEE_BRANCH}"
echo "Log Directory: ${HEE_LOG_DIR}"
```

### Validate Safe Paths

```bash
if [[ "${FILE_PATH}" != "${HEE_REPO_ROOT}/doc/oper/"* ]]; then
    echo "ERROR: Attempting to write outside safe paths"
    exit 1
fi
```

## Security Notes

**WARNING:** Do not leak secrets in logs or environment variables.

```bash
# Bad - secrets in logs
export API_TOKEN="secret123"
echo "Using token: ${API_TOKEN}"  # Logs the secret

# Good - redact secrets
export API_TOKEN="secret123"
echo "Using token: [REDACTED]"  # Safe logging
```

### Operational Rules

- Never commit secrets to the repository
- Redact tokens from logs before sharing
- Use environment variables for sensitive data
- Clear sensitive environment variables after use
- Validate all file paths against `HEE_SAFE_PATHS`
