# hee-attach(1)

```
hee-attach

Attaches HEE policy to a repo locally without committing doctrine into the repo.

Usage:
  tooling/bin/hee-attach --target <repo_path> [--hee <hee_repo_path>]

Effect:
  - Creates .hee/policy/{prompts,docs} inside target repo (local-only)
  - Syncs HEE prompts into .cursor/prompts (local-only)
  - Adds .hee/ and .cursor/ to local exclude suggestions (prints commands)
```
