# State Capsule Template

Use this template for creating State Capsules to ensure consistent handoffs between agents or chat sessions within the Human Execution Engine (HEE) ecosystem.

## Template Structure

```yaml
chat: <project-name> <phase/session>
purpose: <one-sentence objective>
context:
  - Project: <project description>
  - Current Phase: <current phase or milestone>
  - Status: <current status and recent progress>
  - Constraints: <important constraints or requirements>
  - Dependencies: <key dependencies or blockers>
  - Tools/Technologies: <key tools, frameworks, or technologies in use>
  - HEE Integration: <HEE-specific integration points and requirements>

decisions:
  - <specific decision made with rationale>
  - <technical choice and why it was chosen>
  - <architectural decision and its impact>
  - <any trade-offs that were considered>
  - <HEE-specific decisions and their implications>

open_threads:
  - <unresolved issue or pending task>
  - <dependency or blocker>
  - <next major milestone>
  - <risk or concern that needs attention>
  - <question that needs answering>
  - <HEE-specific open items>

next_chat_bootstrap:
  - <immediate next step to take>
  - <how to continue current work>
  - <what to investigate or implement>
  - <priority order for remaining tasks>
  - <HEE-specific bootstrap instructions>
```

## Quick Reference Guide

### Required Fields

| Field                | Description                                  | HEE Integration |
| -------------------- | -------------------------------------------- | --------------- |
| `chat`               | Name of the current session                  | Project + phase identifier |
| `purpose`            | One-sentence objective                       | HEE goal alignment |
| `context`            | Essential background information             | HEE state preservation |
| `decisions`          | Key decisions made                           | HEE decision tracking |
| `open_threads`       | Unresolved items                             | HEE priority management |
| `next_chat_bootstrap`| Starting points for continuation             | HEE execution continuity |

### Formatting Rules

- **Format**: YAML structure
- **Lists**: Use bullet points for all list items
- **Specificity**: Be specific and actionable
- **Rationale**: Include reasoning for decisions
- **Prioritization**: Order open threads by importance
- **HEE Context**: Include HEE-specific considerations

### Content Guidelines

**Context Section**:

- Project overview and HEE integration points
- Current phase and milestone status
- Recent progress and HEE state updates
- Critical constraints and HEE requirements
- Key dependencies and HEE ecosystem blockers
- Tools/technologies with HEE compatibility notes

**Decisions Section**:

- Specific decisions with HEE impact analysis
- Technical choices and HEE architecture alignment
- Architectural decisions and HEE system impact
- Trade-offs considered with HEE implications
- HEE-specific decisions and rationale

**Open Threads Section**:

- Unresolved issues with HEE priority
- Dependencies and HEE ecosystem blockers
- Next major milestones with HEE alignment
- Risks with HEE impact assessment
- Questions needing HEE-specific answers

**Next Chat Bootstrap**:

- Immediate next steps with HEE execution context
- Continuation instructions for HEE workflows
- Investigation priorities with HEE focus
- Implementation guidance with HEE best practices
- HEE-specific bootstrap procedures

## Complete Example

```yaml
chat: HEE CI Monitoring Integration
purpose: Integrate MT-logo-render CI monitoring into HEE with state preservation
context:
  - Project: Human Execution Engine CI/CD Monitoring System
  - Current Phase: Integration of MT-logo-render monitoring
  - Status: Core monitoring adapted to HEE, state integration in progress
  - Constraints: Must maintain HEE state capsule compatibility
  - Dependencies: MT-logo-render v1.2.0, HEE core v1.1.5
  - Tools/Technologies: Python 3.8+, GitHub API, jq, HEE state management
  - HEE Integration: Full state capsule support, decision preservation

decisions:
  - Adapt MT monitoring patterns to HEE state capsule format
    Rationale: Ensures consistency with HEE architecture
  - Implement HEE-specific safety protocols in auto-fix engine
    Rationale: Maintains HEE quality discipline requirements
  - Use HEE state versioning for monitoring state compatibility
    Rationale: Enables smooth transitions between HEE versions
  - Integrate HEE spec coverage metrics into monitoring dashboard
    Rationale: Aligns with HEE spec-first principles

open_threads:
  - Complete HEE state capsule validation for monitoring patterns
  - Test HEE-specific rollback procedures with monitoring integration
  - Document HEE monitoring patterns and state requirements
  - Verify HEE spec coverage metrics calculation accuracy
  - Plan HEE v1.2.0 release with integrated monitoring

next_chat_bootstrap:
  - Finalize HEE state capsule structure for monitoring
  - Implement HEE safety protocol validation in auto-fix
  - Test HEE state preservation during monitoring operations
  - Update HEE documentation with monitoring integration guide
  - Prepare HEE v1.2.0 release candidate with monitoring features
```

## HEE-Specific Integration

### State Capsule Requirements

**HEE State Fields**:

```yaml
hee_specific:
  - state_version: <current HEE state version>
  - decision_stability: <HEE decision preservation metrics>
  - spec_coverage: <HEE spec coverage integration>
  - prompt_compatibility: <HEE prompt version compatibility>
```

### Validation Checklist

- [ ] Identified current HEE project phase and status
- [ ] Documented all HEE-relevant decisions with rationale
- [ ] Listed all HEE-specific unresolved issues
- [ ] Defined HEE-aligned next steps
- [ ] Used HEE terminology and conventions
- [ ] Included HEE state preservation requirements
- [ ] Prioritized items with HEE impact assessment
- [ ] Made next steps HEE-execution ready

## Usage Patterns

### 1. HEE Agent Handoffs

**Pattern**: State capsule chain for agent transitions

```sh
HEE Agent A → State Capsule → HEE Agent B → Updated State Capsule → HEE Agent C
```

**Benefits**:

- Preserves HEE context across agent transitions
- Maintains HEE decision continuity
- Enables HEE specialization and workflow optimization

### 2. HEE Release Management

**Pattern**: Release-specific state capsules

```sh
Pre-Release Capsule → Release Capsule → Post-Release Capsule → Maintenance Capsule
```

**Benefits**:

- Clear HEE release phase boundaries
- Comprehensive HEE release documentation
- Decision history for HEE release analysis
- Risk tracking throughout HEE release lifecycle

### 3. HEE Cross-Project Integration

**Pattern**: Ecosystem state capsules

```sh
HEE Core Capsule → MT-logo-render Integration Capsule → tick-task Integration Capsule
```

**Benefits**:

- HEE ecosystem context preservation
- Dependency management across HEE projects
- Integration point documentation
- HEE-wide decision tracking

## Best Practices

### ✅ HEE Recommended Practices

**Practice 1**: HEE-Specific Context

```yaml
context:
  - HEE Integration: Full state capsule support required
  - HEE Constraints: Must comply with spec-first discipline
  - HEE Dependencies: Core v1.1.5+, prompts v17+
```

**Practice 2**: HEE Decision Rationale

```yaml
decisions:
  - Use HEE canonical prompts for all agent interactions
    Rationale: Ensures HEE editor-agnostic consistency
    Impact: Maintains HEE governance compliance
```

### ❌ HEE Anti-Patterns to Avoid

**Anti-Pattern 1**: Generic HEE Context

```yaml
context:
  - Project: Some HEE project  # Too generic for HEE
```

**Anti-Pattern 2**: Missing HEE Integration

```yaml
next_chat_bootstrap:
  - Continue HEE work  # Too vague for HEE execution
```

**Anti-Pattern 3**: Ignoring HEE State Requirements

```yaml
decisions:
  - Change state format without HEE compatibility  # Violates HEE principles
```

## Integration with HEE Workflow

### 1. HEE Git Integration

**HEE-Specific Practices**:

- Version control all HEE state capsules
- Include capsule references in HEE commit messages
- Link capsules in HEE pull request descriptions
- Use in HEE release notes with state transitions

### 2. HEE CI/CD Integration

**HEE Integration Points**:

- Generate HEE capsule summaries in build artifacts
- Include HEE capsule links in deployment notifications
- Use HEE capsule metadata for project status updates
- Validate HEE capsule structure in documentation checks

### 3. HEE Project Management

**HEE Usage Patterns**:

- Reference in HEE sprint planning and retrospectives
- Use for HEE knowledge transfer during team changes
- Include in HEE project documentation and wikis
- Link to relevant capsules in HEE issue tracking

## HEE Template Management

### 1. Template Location and Usage

**HEE Template Structure**:

```sh
docs/TEMPLATES/
└── STATE_CAPSULE_TEMPLATE.md  # This file
```

**HEE Usage Commands**:

```bash
# Create new HEE capsule from template
cp docs/TEMPLATES/STATE_CAPSULE_TEMPLATE.md docs/history/state_capsules/$(date +%Y-%m-%d)/HEE-Session.md

# Validate the object envelope
tooling/ci/hee-lint
```

### 2. HEE Directory Management

**HEE Automation Scripts**:

```bash
# Create HEE date directory if needed
mkdir -p docs/history/state_capsules/$(date +%Y-%m-%d)

# Find latest HEE capsule
LATEST_HEE=$(ls -dt docs/history/state_capsules/*/ | head -1)/HEE-*.md
```

## HEE-Specific Validation

### 1. HEE Content Requirements

**HEE-Specific Checks**:

- HEE state version compatibility
- HEE decision preservation requirements
- HEE spec coverage integration
- HEE prompt compatibility
- HEE execution continuity

### 2. HEE Structural Validation

**HEE Validation Rules**:

- All required HEE sections present
- HEE YAML format compliance
- HEE naming conventions followed
- HEE date and version references accurate
- HEE file organization maintained

This HEE-specific State Capsule Template provides the foundation
for consistent, reliable handoffs within the Human Execution Engine
ecosystem while maintaining full compatibility with HEE's core principles and architecture.
