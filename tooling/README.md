# HEE Tooling

This directory contains *derivative* tools for distributing and validating Human Execution Engine (HEE) doctrine.

Authoritative doctrine:

- docs/
- prompts/
- contracts/

Tools:

- tooling/bin/hee-vendor  : vendor doctrine into a repo (vendored mode)
- tooling/bin/hee-attach  : attach doctrine locally without committing it (detached mode)
- tooling/bin/hee-sync-cursor-prompts : derive .cursor/prompts from the active policy source
- tooling/bin/hee-check   : boundary/compliance checks
- tooling/bin/hee-ticket  : `-new "description"` / `-list` -- real, minimal first step of an
  internal ticket system (GitHub Issues is an external dependency for all of TCOS's tracking
  right now, same class of concern as `primitives`'s dependency-removal work). Stores one real
  YAML record per ticket in `.hee/tickets/` (sibling of `.hee/spool/`'s existing phase-tracking
  records, not a new convention). Prototype/dogfood, not yet declared standard practice over
  GitHub Issues. See `examples/hee-ticket-output.md`.
- tooling/bin/hee-stat    : stat(1)'s `-c FORMAT` interface, applied to namespaced
  resources instead of the filesystem -- `hee stat -c %W gh/OWNER/REPO` for a repo's
  real creation epoch, same convention as `stat -c %W somefile`. First namespace: `gh/`
  (GitHub users/repos, via `gh api`). Real specifiers reuse `stat`'s actual semantics
  (`%W`=birth time, `%Y`=mtime, `%U`=owner, `%n`=name) plus two TCOS convenience
  aliases (`%REPO`, `%ORG`). See `examples/hee-stat-output.md`.
