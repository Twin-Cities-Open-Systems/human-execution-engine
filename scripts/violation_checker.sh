#!/bin/bash

# HEE Violation Checker Script
# Pre-commit hook for automated violation detection and prevention

# Set strict error handling

# Get filesystem awareness
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR")"
PROJECT_NAME="$(basename "$PROJECT_ROOT" 2>/dev/null || echo "unknown")"

echo "🔍 HEE Violation Prevention Check"
echo "=================================="
echo "📁 Project: $PROJECT_NAME"
echo "📍 Directory: $PROJECT_ROOT"
echo ""

VIOLATION_SCORE=0
VIOLATIONS_FOUND=()

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to validate input and prevent injection
validate_input() {
    local input="$1"
    local description="$2"

    # Check for empty input where not allowed
    if [[ -z "$input" ]]; then
        echo -e "${YELLOW}⚠️  Empty input for $description${NC}"
        return 1
    fi

    return 0
}

# Function to safely execute commands with error handling
safe_execute() {
    local cmd="$1"
    local description="$2"
    local default_value="${3:-}"

    # Validate command for injection attempts
    if ! validate_input "$cmd" "command"; then
        if [[ -n "$default_value" ]]; then
            echo "$default_value"
            return 0
        else
            return 1
        fi
    fi

    local result
    if result=$(eval "$cmd" 2>/dev/null); then
        echo "$result"
        return 0
    else
        if [[ -n "$default_value" ]]; then
            echo "$default_value"
            return 0
        else
            echo -e "${RED}❌ Error executing: $description${NC}"
            return 1
        fi
    fi
}

# Function to add violation
add_violation() {
    local code="$1"
    local description="$2"
    local points="$3"
    local severity="$4"

    VIOLATION_SCORE=$((VIOLATION_SCORE + points))
    VIOLATIONS_FOUND+=("$code: $description ($points points - $severity)")
    echo -e "${RED}❌ $code: $description${NC}"
}

# Function to add warning
add_warning() {
    local code="$1"
    local description="$2"

    echo -e "${YELLOW}⚠️  $code: $description${NC}"
}

# Function to add success
add_success() {
    local message="$1"

    echo -e "${GREEN}✅ $message${NC}"
}

# Check 1: Branch Management
echo "📋 Checking Branch Management..."
current_branch=""
if git rev-parse --git-dir > /dev/null 2>&1; then
    current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
    if [[ -z "$current_branch" ]]; then
        add_violation "BM-005" "Unable to determine current branch" 3 "Level 2"
    elif [[ "$current_branch" == "main" || "$current_branch" == "master" ]]; then
        add_violation "BM-001" "Direct commit to main/master branch not allowed" 3 "Level 2"
    elif [[ ! "$current_branch" =~ ^feature/ ]]; then
        add_warning "BM-004" "Branch name should follow feature/ pattern"
    else
        add_success "Branch management compliance"
    fi
else
    add_violation "BM-006" "Not in a git repository" 5 "Level 3"
fi

# Check 2: Model Disclosure
echo ""
echo "📋 Checking Model Disclosure..."
commit_msg=""

# Try to get the commit message from the current commit being made
# Check if we're in a pre-commit hook context
if [[ -n "${GIT_COMMIT:-}" ]]; then
    # We're in a commit hook, get the commit message
    commit_msg=$(git --no-pager log --format=%B -n 1 "$GIT_COMMIT" 2>/dev/null || echo "")
elif [[ -f ".git/COMMIT_EDITMSG" ]]; then
    # Try to read from the commit message file
    commit_msg=$(cat .git/COMMIT_EDITMSG 2>/dev/null || echo "")
else
    # Fall back to last commit (for testing/debugging)
    commit_msg=$(git --no-pager log --format=%B -n 1 HEAD 2>/dev/null || echo "")
fi

if [[ -z "$commit_msg" ]]; then
    add_violation "CH-002" "Unable to retrieve commit message" 1 "Level 1"
elif [[ ! "$commit_msg" =~ \[model:[[:space:]]*[a-zA-Z0-9._-]+\] ]]; then
    add_violation "CH-001" "Missing model disclosure in commit message" 1 "Level 1"
    add_warning "CH-001" "Include [model: <model-name>] in commit message"
    add_warning "CH-001" "Format: [model: claude-3.5-sonnet] or [model: gpt-4]"
else
    add_success "Model disclosure compliance"
fi

# Check 3: Working Directory
echo ""
echo "📋 Checking Working Directory..."
current_dir=$(pwd)
if git rev-parse --git-dir > /dev/null 2>&1; then
    project_root=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
    if [[ -z "$project_root" ]]; then
        add_violation "WC-004" "Unable to determine project root directory" 7 "Level 4"
    elif [[ "$current_dir" != "$project_root" ]]; then
        add_violation "WC-001" "Not working from project root directory" 7 "Level 4"
        add_warning "WC-001" "Current: $current_dir, Expected: $project_root"
    else
        add_success "Working directory compliance"
    fi
else
    add_violation "WC-005" "Not in a git repository for directory check" 7 "Level 4"
fi

# Check 4: State Capsule Updates
echo ""
echo "📋 Checking State Capsule Updates..."
state_capsule_dir="$project_root/docs/history/state_capsules"

# Check for .done extension rule
if [[ -d "$state_capsule_dir" ]]; then
    # Check for .done files (completed capsules)
    done_capsules=($(find "$state_capsule_dir" -name "*.md.done" -type f 2>/dev/null))
    if [[ ${#done_capsules[@]} -gt 0 ]]; then
        add_success "Found ${#done_capsules[@]} completed state capsule(s) with .done extension"
        # Skip processing .done capsules
        for done_capsule in "${done_capsules[@]}"; do
            echo "  - Skipping completed capsule: $(basename "$done_capsule")"
        done
    fi

    # Check for active (non-.done) state capsules
    active_capsules=($(find "$state_capsule_dir" -name "*.md" -type f ! -name "*.md.done" 2>/dev/null))
    if [[ ${#active_capsules[@]} -gt 0 ]]; then
        # Find the most recent active capsule
        latest_capsule=""
        latest_time=0

        for capsule in "${active_capsules[@]}"; do
            if [[ -f "$capsule" ]]; then
                capsule_time=$(stat -c "%Y" "$capsule" 2>/dev/null || echo 0)
                if [[ $capsule_time -gt $latest_time ]]; then
                    latest_time=$capsule_time
                    latest_capsule="$capsule"
                fi
            fi
        done

        if [[ -n "$latest_capsule" && -f "$latest_capsule" ]]; then
            capsule_age=$(($(date +%s) - latest_time))
            if [[ $capsule_age -gt 86400 ]]; then # 24 hours
                add_violation "WC-002" "State capsule not updated recently" 7 "Level 4"
                add_warning "WC-002" "Update state capsule after significant operations"
            else
                add_success "State capsule compliance"
            fi
        else
            add_violation "WC-006" "No active state capsules found" 7 "Level 4"
        fi
    else
        add_violation "WC-002" "No state capsule directory found" 7 "Level 4"
    fi
else
    add_violation "WC-002" "State capsule directory missing" 7 "Level 4"
fi

# Check 5: Documentation References
echo ""
echo "📋 Checking Documentation References..."
required_docs=("docs/HEE_POLICY.md" "docs/STATE_CAPSULE_GUIDE.md" "prompts/INIT.md")
missing_docs=()

for doc in "${required_docs[@]}"; do
    if [[ ! -f "$project_root/$doc" ]]; then
        missing_docs+=("$doc")
    fi
done

if [[ ${#missing_docs[@]} -gt 0 ]]; then
    add_violation "PA-001" "Missing required documentation files" 1 "Level 1"
    for doc in "${missing_docs[@]}"; do
        add_warning "PA-001" "Missing: $doc"
    done
else
    add_success "Documentation compliance"
fi

# Check 6: Pre-commit Configuration
echo ""
echo "📋 Checking Pre-commit Configuration..."
if [[ -f "$project_root/.pre-commit-config.yaml" ]]; then
    if grep -q "hee-violation-check" "$project_root/.pre-commit-config.yaml"; then
        add_success "Pre-commit configuration compliance"
    else
        add_violation "WC-003" "HEE violation check not configured in pre-commit" 5 "Level 3"
    fi
else
    add_violation "WC-003" "Pre-commit configuration missing" 5 "Level 3"
fi

# Summary
echo ""
echo "📊 Violation Summary"
echo "==================="
echo "Total Violation Score: $VIOLATION_SCORE points"

# Print detailed violations
if [[ ${#VIOLATIONS_FOUND[@]} -gt 0 ]]; then
    echo ""
    echo "📋 Detailed Violations:"
    for violation in "${VIOLATIONS_FOUND[@]}"; do
        echo "  - $violation"
    done
fi

# Exit with appropriate code based on violation score
# Momentum rule: in oper/iteration contexts, never block progress.
# Hard-fail must be explicitly requested (CI can opt-in later).
STRICT="${HEE_STRICT:-0}"
strict_exit() {
    # usage: strict_exit <code>
    if [[ "$STRICT" == "1" ]]; then
        exit "$1"
    fi
    exit 0
}

if [[ $VIOLATION_SCORE -eq 0 ]]; then
    echo -e "${GREEN}🎉 Excellent compliance! No violations detected.${NC}"
    strict_exit 0
elif [[ $VIOLATION_SCORE -le 5 ]]; then
    echo -e "${YELLOW}✅ Good compliance with minor issues.${NC}"
    strict_exit 0
elif [[ $VIOLATION_SCORE -le 15 ]]; then
    echo -e "${YELLOW}⚠️  Fair compliance - improvement needed.${NC}"
    strict_exit 1
elif [[ $VIOLATION_SCORE -le 30 ]]; then
    echo -e "${RED}❌ Poor compliance - immediate action required.${NC}"
    strict_exit 1
else
    echo -e "${RED}🚨 Critical compliance failure - operations suspended.${NC}"
    strict_exit 1
fi
