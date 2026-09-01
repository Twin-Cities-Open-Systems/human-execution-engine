# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.1.0] - 2026-01-28

### Added

- Hardware discovery specification with GNU name seeds (`gnu-pill`, `gnu-free`)
- Permanent GNU name lock: `gnu-barrow` (COG authority)
- P0 metrics pipeline for GitHub traffic data collection
- State capsule system for governance and audit tracking
- Completion markers for workflow documentation
- Release notes generation and tagging system
- Operations index and status documentation
- `tools/` directory for operator utilities
- `apply-var-patch` tool relocated from `ci/git/` to `tools/git/`

### Changed

- Applied hardware discovery spec updates via standard patch workflow
- Established feature branch development workflow compliance
- Integrated dashboard monitoring capabilities

### Technical Details

- **GNU Name**: gnu-barrow (permanently locked)
- **Tag**: hee-r2-pre-2026-01-28.001-gnu-barrow
- **Branch**: feature/gnu-barrow-lock-2026-01-28
- **Validation**: Pre-commit hooks, HEE doctrine compliance, integration tests
- **Artifacts**: Complete audit trail from patch generation to release

### Infrastructure

- State capsule: `2026-01-28-GNU-BARROW-LOCK.yml`
- Release notes: `docs/releases/hee-r2-pre-2026-01-28.001-gnu-barrow.md`
- Completion record: `docs/history/completions/2026-01-28-HW-DISCOVERY-SPEC-APPLY-0001.yml <!-- hee-check:refs-ok  a changelog records what was true then -->`

---

## Release Process

This release was created following HEE governance standards:

- Feature branch workflow (no direct main commits)
- Pre-commit validation passing
- State capsule and completion marker documentation
- Full audit trail preservation
- Multi-stage validation (smoke tests, integration tests, release gates)

---

*Changelog locked for v0.1.0 release - further entries require new version tags*
