# Repo Identity Contract (v1)

## Purpose

Define a scheme-based identity for repos that does not lock to a single host or transport.

## repo_key_input

Canonical identity input string:

`<vcs_scheme>://<vcs_authority>/<repo_slug>`

Examples:
- `https://github.com/owner/repo`
- `rsync://host/module/path` (normalize rsync shorthand `host::module/path` to this form)

## repo_key_full

`repo_key_full = sha256(repo_key_input_normalized)`

Normalization (minimum):
- scheme: lowercase
- authority: lowercase; strip trailing `/`
- slug: strip leading `/`; collapse repeated `/`; strip trailing `/`
