# GCIC v1 (General Contract Interface Contract)

## Purpose

Defines how contracts are authored, stored, and referenced.

## Rules (normative)

- Contracts MUST live in-repo.
- Contract changes MUST ship via PR.
- Evidence-first: every behavioral claim should have a reproducer + captured output.
- No-clobber is A1 when writing files (default refuse overwrite).
- Agent-Sig: any emission governed by a contract (issue/PR comment, commit,
  contract signature) MUST carry a real identity signature, produced by
  `tools/agent-signature.sh` per `contracts/agent-instance-signature-v1.contract.yaml`
  — session id, pid, tmux URI (or `none`), messaging socket, gh actor,
  timestamp, all read live from the process's own environment, never
  hand-assembled. Use `tools/agent-signature.sh --footer` to append it to
  a comment. Purpose: disambiguate which specific agent instance/session
  produced an emission when multiple share one identity (real need, not
  hypothetical — see human-execution-engine#308, and fleet-ops#257, where
  a hand-rolled tmux self-identification turned out to be wrong and the
  real tool caught it). This rule does not invent a second mechanism — an
  earlier draft of this rule tried to and was corrected once the existing
  contract was found.

## Interface

- Higher-level contracts inherit GCIC unless explicitly exempted.
