# HEE Policy and Governance

## Overview

This document defines the policies and governance rules for the
Human Execution Engine (HEE) ecosystem, ensuring consistent behavior
and preventing violations of HEE principles.

## Core HEE Policies

### 1. Output Pager Prevention Policy

**CRITICAL HEE VIOLATION**: Output MUST never invoke shell PAGER

**Rationale**: Pager invocation requires oper intervention, violating HEE autonomy and deterministic execution principles.

**Enforcement**:

- All shell commands must include pager prevention when applicable
- Pager bypass required for ALL interactive commands
- Violation constitutes HEE process failure
- Document pager prevention in all command examples

**Command-Specific Requirements**:

- **Git**: Use `--no-pager` flag or `GIT_PAGER=cat` environment variable
- **Man pages**: Use `-P cat` flag or `MANPAGER=cat` environment variable
- **Less/More**: Use `cat` or redirect to file instead
- **Grep**: Use `--no-pager` where available, otherwise redirect output
- **Find**: Use `-print0` with `xargs -0` or redirect to file
- **System commands**: Use `PAGER=cat` environment variable or output redirection

**Examples**:

```bash
# CORRECT: Pager prevention included
git --no-pager log
GIT_PAGER=cat git status
man -P cat page
PAGER=cat command
command | cat
command > file.txt

# INCORRECT: Pager invocation allowed
git --no-pager log         # Prevents pager invocation
man page                   # May invoke pager
command                    # May invoke pager
```

### 2. Branch Management Policy

**Requirement**: ALL changes MUST use feature branches

**Enforcement**:

- Never commit directly to main branch
- Feature branches named: `feature/description-of-work`
- Delete merged branches immediately to prevent confusion
- All changes made on feature branches only

**Workflow**:

```bash
git checkout -b feature/work-description
# Make changes, commit frequently
git push origin feature/work-description
gh pr create --base main --head feature/work-description
# Wait for merge, then cleanup
git checkout main && git pull origin main
git branch -D feature/merged-branch  # Local
git push origin --delete feature/merged-branch  # Remote
```

### 3. State Preservation Policy

**Requirement**: HEE state MUST be preserved across all operations

**Enforcement**:

- Update state capsule after every phase
- Document all state changes
- Maintain state consistency throughout session
- Never leave repository in inconsistent state

**State Capsule Requirements**:

- All required sections present
- HEE YAML format compliance
- HEE naming conventions followed
- HEE date and version references accurate

### 4. Security Validation Policy

**Requirement**: Security validation BEFORE any implementation

**Enforcement**:

- All inputs validated against HEE/HEER security requirements
- No shell commands without security pre-check
- Content sanitization required for all user inputs
- Threat model verification mandatory

**Security Checks**:

- Unicode validation for all text inputs
- Control character blocking
- Zero-width character detection
- Safe character normalization

### 5. Documentation Policy

**Requirement**: Documentation is paramount - no undefined references

**Enforcement**:

- No references to non-existent files/tools
- All README examples must work immediately
- API documentation must reflect actual implementation
- Specs must be canonical and complete

**Documentation Standards**:

- Use relative paths for portability
- Include file references and cross-links for navigation
- Design for smooth handoffs and team onboarding
- Maintain consistency with existing documentation patterns

**Real-Link Requirement**:

- Bare shorthand references to issues/PRs (e.g. `fleet-ops#151`) are not
  sufficient on their own — every reference to an issue, PR, or comment,
  in both GitHub content (issue bodies, comments, PR descriptions) and
  chat/agent output, must be a real markdown link to the actual URL
  (`[fleet-ops#151](https://github.com/Twin-Cities-Open-Systems/fleet-ops/issues/151)`)
- The shorthand text is fine as the link label; the `(url)` is the
  required part
- Rationale: bare shorthand only auto-links inside GitHub's own
  same-org rendering — it renders as dead text everywhere else (chat
  transcripts, cross-repo bodies, anything copy-pasted elsewhere)

### 6. Command Safety Policy

**Requirement**: PRE-VALIDATION required for all commands

**Enforcement**:

- Syntax validation with `bash -n` for all shell commands
- Path verification before file operations
- Git state verification before repository operations
- No execution without explicit validation

**Validation Pattern**:

```bash
# Pattern: Validate then execute
[ -f file.txt ] && echo "File exists" || echo "File missing - plan violation"
```

### 7. Integration Compliance Policy

**Requirement**: HEE/HEER compliance enforced

**Enforcement**:

- All changes validated against HEE conceptual model
- HEER runtime contract compliance required
- Breaking changes require ecosystem coordination
- Integration examples must be executable immediately

### 8. Conflict Prevention Policy

**CRITICAL HEE VIOLATION**: Conflicts must be prevented, not resolved

**Rationale**: Manual conflict resolution wastes tokens and time, violating HEE efficiency principles.

**Enforcement**:

- Mandatory daily rebasing for active branches
- Automated conflict detection in pre-commit hooks
- Merge readiness validation required before PR creation
- Branch health monitoring and alerts

**New HEE Rules**:

#### Rule 1: Mandatory Daily Rebase

**Requirement**: All active feature branches must be rebased onto main daily
**Enforcement**: Automated validation in CI/CD pipeline
**Exception**: Branches inactive for more than 48 hours

#### Rule 2: Pre-Commit Conflict Detection

**Requirement**: All commits must pass conflict detection validation
**Enforcement**: Pre-commit hooks with automated conflict checking
**Scope**: All file types and modifications

#### Rule 3: Merge Readiness Validation

**Requirement**: All PRs must pass merge readiness validation before review
**Enforcement**: Automated validation in pull request checks
**Criteria**: No conflicts, up-to-date with main, passing all tests

#### Rule 4: Branch Health Monitoring

**Requirement**: All branches must maintain acceptable health scores
**Enforcement**: Automated monitoring and alerts
**Threshold**: Health score below 80% triggers mandatory rebase

**Implementation**:

```bash
# Pre-commit hook for conflict detection
#!/bin/bash
# Check for potential conflicts before commit
git fetch origin
git diff origin/main...HEAD --exit-code
```

**Examples**:

```bash
# CORRECT: Conflict prevention practices
git checkout feature/work
git fetch origin
git rebase origin/main
git push origin feature/work

# INCORRECT: Conflict creation practices
# Working on stale branch without rebasing
# Pushing without checking merge readiness
# Creating PR without conflict validation
```

### 9. Token Optimization Policy

**Requirement**: Token usage must balance efficiency with process integrity

**Rationale**: Short-term token savings should not compromise long-term process efficiency.

**Enforcement**:

- Cost-benefit analysis for optimization decisions
- Token usage monitoring and reporting
- Automated decision-making for routine optimizations
- Manual override available for complex scenarios

**Guidelines**:

- Regular rebasing costs vs. conflict resolution costs
- Automated systems should handle routine optimization
- Token efficiency should not compromise code quality
- Process integrity takes precedence over token optimization

### 10. Ticket & PR Ownership Policy

**Requirement**: every issue and PR must have a clear owner or a labeled
reason it doesn't

**Enforcement**:

- Self-assign any ticket or PR you create, unless explicitly directed
  otherwise
- Apply correct labels from the repo's existing label set — never create
  a new label; if one is genuinely needed, file a ticket for it, assign
  that ticket to `@spencerbutler`, and report the request in chat
- Unassigned tickets/PRs must be the rare exception, not the default —
  each one needs a label that denotes why no owner is assigned (e.g.
  blocked on a decision, needs triage)
- Close tickets as soon as their work is actually done — don't let
  finished or stale work sit open



### HEE Rule Violation Documentation

**Process**:

1. **Immediate**: Document violation in state capsule
2. **Analysis**: Identify root cause and impact
3. **Resolution**: Record corrective actions taken
4. **Prevention**: Add measures to prevent recurrence

**Violation Categories**:

- **Critical**: Pager invocation, direct main commits, state corruption
- **High**: Security violations, documentation failures
- **Medium**: Command safety issues, integration problems
- **Low**: Minor policy violations, formatting issues

**Example Violation Report**:

```markdown
## 🚨 HEE Rule Violation Documentation

### **Violation**: Direct Main Branch Commit
**Date**: 2026-01-24 at 17:42:52 CST
**Commit**: `7f4bd4f` - "feat: Add human-readable timestamps"
**Issue**: Created files/changes directly on main branch instead of feature branch

### **Root Cause Analysis**:
- Assumed minor formatting changes were acceptable on main
- Failed to follow "ALWAYS create feature branches" rule

### **Impact**:
- ❌ Violates HEE governance and change tracking
- ❌ Breaks established workflow standards

### **Corrective Action Taken**:
- ✅ **Immediate**: Reverted main branch changes (commit `fa16f86`)
- ✅ **Proper Process**: Changes moved to feature branch workflow
- ✅ **Documentation**: Violation recorded in state capsule

### **Status**: RESOLVED ✅
```

## Compliance Monitoring

### Regular Audits

- **Daily**: Review state capsule for violations
- **Weekly**: Audit branch management compliance
- **Monthly**: Review security and documentation standards

### Automated Checks

- Pre-commit hooks for HEE compliance
- State capsule validation in CI/CD
- Pager prevention validation in command examples

### Enforcement Actions

- **First violation**: Warning and documentation
- **Repeated violations**: Process review and training
- **Critical violations**: Immediate corrective action required

## Policy Updates

### Version Control

- All policy changes tracked in git
- Model disclosure required for policy commits
- State capsule updates for policy changes

### Review Process

- Policy reviews every 3 months
- Community feedback incorporated
- HEE principles maintained as core

## References

- [HEE Definition](HEE.md)
- [Prompting Rules](../prompts/PROMPTING_RULES.md)
- [State Capsule Guide](STATE_CAPSULE_GUIDE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

---

**These policies are ENFORCEMENT RULES, not guidelines. Violation constitutes process failure.**
