# Filesystem Hierarchy Policy (v1)

Rule:
- Follow the target OS hierarchy documentation (hier(7) or equivalent) when available.
- Fallback/default convention: BSD-style `/usr/local` prefix for system-scope installs, adjusted to match local OS guidance.

Scope:
- home-scope: `$HOME/.hee`
- repo-scope: `<repo>/.hee` (scratch; never committed) and `<repo>/hee` (source)
- system-scope: per-OS hierarchy docs
