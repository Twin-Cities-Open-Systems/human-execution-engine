# GCIC v1 (General Contract Interface Contract)

## Purpose

Defines how contracts are authored, stored, and referenced.

## Rules (normative)

- Contracts MUST live in-repo.
- Contract changes MUST ship via PR.
- Evidence-first: every behavioral claim should have a reproducer + captured output.
- No-clobber is A1 when writing files (default refuse overwrite).
- Agent-Sig: any emission governed by a contract (issue/PR comment, commit,
  contract signature) MUST carry a slim identity line — `Agent-Sig:
  <login>@<host>:<tmux-session>` — anchored to the real SOA identity
  capsule (`~/.hee/index/_.yaml`) per the existing `verify_identity_before_emit`
  invariant (see `hee/contracts/gcic-dric-mdshell.contract.v1.md`). For
  higher-stakes emissions (contract ratification, security findings), append
  the capsule's `stool_hash_show`: `Agent-Sig: <login>@<host>:<tmux-session>
  (stool <short-hash>)`. Purpose: disambiguate which specific agent
  instance/session produced an emission when multiple share one identity
  (real need, not hypothetical — see human-execution-engine#308).

## Interface

- Higher-level contracts inherit GCIC unless explicitly exempted.
