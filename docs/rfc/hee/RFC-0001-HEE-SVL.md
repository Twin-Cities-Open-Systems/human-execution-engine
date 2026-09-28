# RFC-0001: HEE SVL

## Status

Accepted. Implementation completed with recovery packet commit 1f98bf0.

## Problem Statement

HEE execution requires verifiable operational boundaries to prevent:

- Execution claims without disk evidence
- Authority scope confusion across agent-operator interactions
- Signal inference from silence without declared observation scope
- Violation classification as moral rather than factual states
- Unverifiable state preservation claims

Without explicit signal-level constraints, operational drift accumulates until recovery becomes impossible.

## Constraints

### Human Misuse Risks

- Operators may claim execution without verifiable artifacts
- Agents may overstep authority boundaries through implication
- Signal silence may be misinterpreted as system absence
- Violations may be treated as personal failings rather than system states

### Over-Aggregation Risks

- Authority may expand beyond declared signal-level scope
- Signal classification may become aspirational rather than enumerable
- State preservation may claim global rather than scoped validity
- Recovery operations may attempt doctrine creation without gates

### Authority Confusion Risks

- Agent-operator boundaries may blur through informal communication
- Signal routing may bypass explicit authority declarations
- Execution evidence may be claimed through chat rather than disk
- Scope constraints may be inherited rather than explicitly declared

## Considered Alternatives

### Alternative 1: Implicit Authority

Allow authority to be implied through operational patterns rather than explicit declaration.
Rejected: Creates authority confusion risks and prevents deterministic boundary enforcement.

### Alternative 2: Global Scope

Apply signal constraints universally across all HEE components.
Rejected: Over-aggregation risk and boundary violation of operational contracts.

### Alternative 3: Moral Classification

Treat violations as moral failures requiring judgment.
Rejected: Human misuse risk and factual state distortion.

### Alternative 4: Chat-Based Evidence

Accept execution claims supported by conversation history.
Rejected: Eliminates disk truth requirement and enables unverifiable claims.

### Alternative 5: Aspirational Taxonomy

Allow signal classes to evolve through usage patterns.
Rejected: Prevents deterministic classification and validation.

## Decision

Implement explicit SVL doctrine with atomic invariants derived from operational recovery requirements:

1. Authority limited to signal-level constructs with explicit boundary declarations
2. Scope constrained to signal validation, classification, and routing within HEE contexts
3. Core invariants treating silence as operational construct, violations as factual states, requiring disk evidence for claims
4. Explicit non-goals preventing moral guidance, intent interpretation, content generation

Supporting specifications define signal taxonomy and glyph ring encoding rules without extending doctrine scope.

## Consequences

### Positive Consequences

- Operational discipline through verifiable execution claims
- Authority confusion prevention via explicit boundary declarations
- Deterministic signal classification through enumerable taxonomy
- Recovery feasibility through disk-backed state preservation
- Implementation scope containment through explicit non-goals

### Negative Consequences

- Increased operational overhead for signal declaration and validation
- Authority constraints may require explicit declarations for routine operations
- Taxonomy limitations prevent classification of undefined signal types
- Recovery requirements demand disk artifact maintenance

### Mitigation

- Automation of signal validation and classification processes
- Pre-commit validation integration for authority verification
- Operational checklists for routine boundary declarations
- State preservation tooling for evidence maintenance

## Acceptance Criteria

- [x] Doctrine defines authority boundaries without global claims
- [x] Core invariants are atomic and independently testable
- [x] Signal taxonomy provides finite, enumerable classifications
- [x] Glyph rings define deterministic encoding without transformation ambiguity
- [x] Recovery packet establishes disk truth with operational gates
- [x] Pre-commit validation enforces authority and scope constraints
