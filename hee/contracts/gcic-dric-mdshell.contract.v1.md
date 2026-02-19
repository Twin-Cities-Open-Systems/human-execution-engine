# gcic→dric→mdshell Contract (v1)

## Purpose

Prevent incorrect emits (wrong repo, wrong path, wrong identity) by requiring deterministic preflight proofs.

## Requirements (emit-capable procedures)

- Anchor to SOA: `~/.hee/index/_.yaml`
- Require invariant token: `verify_identity_before_emit`
  - Legacy token `verify_identity_before_writes` MAY be accepted as a temporary compatibility measure, with warning.
- Repo-proof:
  - Declare `REPO_SLUG`
  - Verify `origin` contains `REPO_SLUG` before any emit/commit/push
- mdshell format:
  - include timestamp format, repo name, GitHub user
  - include verify-first guardrails; fail closed
  - avoid PWD assumptions: always `cd` to verified target
- Language:
  - use “correct action” (not right/wrong)

If it ain’t correct, it ain’t HEE.
