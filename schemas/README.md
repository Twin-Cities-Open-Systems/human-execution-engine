# Schema Layering Doctrine

This repository implements a three-layer schema architecture for managing Human Execution Engine (HEE) specifications:

## Layer 1: Authoritative Schemas

- **Location**: `schemas/hee/v1/`
- **Purpose**: Canonical, authoritative schema definitions
- **Authority**: Final source of truth for all HEE specifications
- **Format**: JSON Schema with strict validation rules

## Layer 2: Runtime Schemas

- **Purpose**: Runtime validation and tooling integration
- **Source**: Generated from Layer 1 schemas
- **Usage**: CI/CD pipelines, development tools, API validation

## Layer 3: Documentation Schemas

- **Purpose**: Human-readable documentation and examples
- **Source**: Derived from Layer 1 with additional context
- **Usage**: Developer guides, API documentation, examples

## Schema Resolution Rules

### Primary Authority

Schema resolution is determined by the tuple `(apiVersion, kind)`:

- `apiVersion`: Version identifier (e.g., "hee/v1")
- `kind`: Resource type identifier (e.g., "Blueprint", "Enforcer")

### $schema Field

The `$schema` field is **optional and informational only**:

- When present, it must match the resolved schema
- When absent, resolution follows the `(apiVersion, kind)` tuple
- No enforcement of `$schema` field presence in this phase

## Layer-1 Authority Declaration

The `schemas/hee/v1/` directory is the authoritative Layer-1 location for all HEE specifications. All other schema layers derive from this source.

- schemas/hee/v1/evidence-pointer.schema.json — validates evidence pointer strings (raw GitHub URL form).
