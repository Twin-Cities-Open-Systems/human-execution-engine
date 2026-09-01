# HEE State Capsule Guide

## Status

OPTIONAL / HISTORICAL LOGGING (NON-AUTHORITATIVE)

## Rules

- State Capsules are historical working notes, not a control-plane mechanism.
- No workflow may REQUIRE State Capsules for handoff, sequencing, or authorization.
- AUTHZ is granted only via explicit chat-line sentinel:
  `AUTHZ: APPROVED_TO_ACT`
- Commit-time authority governs; working notes are provisional.
- If content becomes durable doctrine, it MUST be promoted to `docs/doctrine/`.

## Overview

State Capsules are structured documentation artifacts that preserve critical
project state, decisions, and context between agent sessions. They enable seamless
handoffs and maintain project continuity in the Human Execution Engine (HEE) ecosystem.

## Purpose

State Capsules serve multiple critical functions:

- **Knowledge Preservation**: Capture decisions, context, and progress
- **Contextual Reference**: Provide optional historical context for agents and operators
- **Progress Tracking**: Document what was accomplished and what remains
- **Compliance Assurance**: Maintain HEE governance standards
- **Audit Trail**: Provide historical record of project evolution

## Directory Structure

```sh
docs/history/state_capsules/
├── README.md                    # Directory overview and conventions
├── CURRENT_TASKS.md             # Optional operator dashboard (non-authoritative)
├── 2026-01-24/                  # Date-organized session capsules
│   ├── HEE-Session-Report.md
│   ├── HEE-Implementation-Plan-100-Compliance.md
│   └── [other session capsules]
└── archive/                     # Completed capsules (if needed)
```

## File Naming Convention

### Session Capsules

- **Format**: `Project-Phase-Description.md`
- **Examples**:
  - `HEE-Compliance-Closure.md`
  - `MT-logo-render-Phase3-CI-Troubleshooting.md`
  - `Security-Scanner-Implementation.md`

### Completion Convention

When tasks are complete, prepend `done.` to the filename:

- `Project-Phase-Description.md` → `done.Project-Phase-Description.md`

## Capsule Structure

### Required Sections

```yaml
chat: <project-name> <phase/session>
purpose: <one-sentence objective>
context:
  - Project: <project description>
  - Current Phase: <current phase or milestone>
  - Status: <current status and recent progress>
  - Constraints: <important constraints or requirements>
  - Dependencies: <key dependencies or blockers>

decisions:
  - <specific decision made with rationale>
  - <technical choice and why it was chosen>
  - <architectural decision and its impact>

open_threads:
  - <unresolved issue or pending task>
  - <dependency or blocker>
  - <next major milestone>

next_chat_bootstrap:
  - <immediate next step to take>
  - <how to continue current work>
  - <what to investigate or implement>
```

## Usage Guidelines

### For Session Capsules

1. **Create at Session Start**: Document initial context and objectives
2. **Update During Session**: Capture decisions and progress
3. **Complete at Session End**: Mark completed tasks and plan next steps
4. **Rename on Completion**: Prepend `done.` when all tasks finished

### For Current Tasks Capsule

1. **Single Source of Truth**: Always check `CURRENT_TASKS.md` first
2. **Update After Major Changes**: Reflect new phases or priorities
3. **Cross-Reference Sessions**: Link to detailed session capsules
4. **Maintain Accuracy**: Keep status current and actionable

## Workflow Integration

### Git Workflow

- State Capsules are version controlled with project code
- Include capsule references in commit messages for major transitions
- Capsules provide context for PR reviews and merges

### CI/CD Integration

- Capsules can trigger automated validation
- Status updates can inform build processes
- Compliance checks can reference capsule state

### Agent Handoffs

- **Incoming Agent**: Read latest capsule to understand current state
- **Outgoing Agent**: Update capsule with progress and next steps
- **Context Preservation**: Ensure no knowledge loss between sessions

## Best Practices

### Content Guidelines

- **Be Specific**: Include concrete details, not vague descriptions
- **Document Rationale**: Explain why decisions were made
- **Prioritize Threads**: Rank open issues by importance
- **Actionable Next Steps**: Provide clear, immediate actions

### Maintenance

- **Regular Updates**: Keep capsules current with project state
- **Archive Completed**: Move old capsules if directory becomes cluttered
- **Cross-Reference**: Link related capsules and documentation
- **Quality Assurance**: Review capsules for completeness and accuracy

### Compliance

- **HEE Standards**: Follow established governance rules
- **Pager Prevention**: Ensure all commands prevent pager invocation
- **Model Disclosure**: Include model information in commits
- **Branch Management**: Use feature branches for all changes

## Examples

### Session Capsule Example

```yaml
chat: HEE Compliance Closure
purpose: Resolve remaining violations to achieve 100% HEE compliance
context:
  - Project: human-execution-engine governance optimization
  - Current Phase: Phase 1 (Compliance closure)
  - Status: 3 active violations (5 points total)
  - Constraints: Must maintain existing HEE framework
  - Dependencies: Access to violation tracking system

decisions:
  - Create feature branch for all changes (resolves BM-001)
  - Implement model disclosure in commit messages (resolves CH-001)
  - Create STATE_CAPSULE_GUIDE.md documentation (resolves PA-001)

open_threads:
  - Update violation metrics to reflect zero-point status
  - Test compliance improvements

next_chat_bootstrap:
  - Create docs/STATE_CAPSULE_GUIDE.md with comprehensive guide
  - Update CURRENT_TASKS.md to reflect completion
  - Prepare for Phase 2 implementation plan execution
```

### Current Tasks Capsule Example

```yaml
## Quick Status Summary

- **Active Tasks**: 3 (Compliance closure items)
- **Completed Tasks**: 23 (Core + advanced features)
- **Open PRs**: 0 (Clean state)
- **Branch Status**: Clean main branch
- **Critical Alerts**: 0 (Target achieved)

## Active Tasks

### 🔴 Phase 1: Compliance Closure (HIGH PRIORITY)

- [x] Create feature branch for all changes
- [x] Implement model disclosure in commit messages
- [x] Create docs/STATE_CAPSULE_GUIDE.md documentation
- [ ] Update violation metrics to zero-point status
- [ ] Commit with proper HEE format

**Goal**: Achieve 100% HEE compliance (0 violation points)
```

## Troubleshooting

### Common Issues

- **Missing Context**: Always include essential background information
- **Vague Next Steps**: Make actions specific and immediately actionable
- **Outdated Information**: Keep capsules current with project state
- **Incomplete Documentation**: Ensure all required sections are filled

### Recovery Procedures

1. **Stale Capsule**: Update with current project state
2. **Missing Information**: Cross-reference with other capsules or documentation
3. **Conflicting Information**: Resolve discrepancies and update accordingly
4. **Incomplete Tasks**: Document current status and next steps

## Integration Points

### Related Documentation

- `docs/HEE_POLICY.md` - Governance rules and standards
- `prompts/PROMPTING_RULES.md` - The agent-facing rulebook

### Tools and Scripts

- `scripts/violation_checker.sh` - Compliance validation
- `scripts/check_pager_prevention.sh` - Pager prevention validation
- `scripts/check_model_disclosure.sh` - Model disclosure validation

## Evolution and Updates

### Version History

- **v1.0**: Initial state capsule framework
- **v1.1**: Added completion convention (`done.` prefix)
- **v1.2**: Enhanced compliance tracking and validation

### Future Enhancements

- Automated capsule generation from session logs
- Integration with project management tools
- Enhanced validation and cross-referencing
- AI-assisted capsule completion and suggestions

## Conclusion

State Capsules are the backbone of HEE project continuity and governance.
By maintaining comprehensive, current, and well-structured capsules, the
system ensures that critical project knowledge is preserved, decisions are
documented, and seamless handoffs between agents are possible.

**Remember**: A well-maintained state capsule system is the difference between chaotic project handoffs and smooth, efficient development continuity.
