---
name: ratify-contract
description: GPG-ratify a HEE Contract (status:proposed -> status:ratified) with correct sign-then-commit ordering. Use whenever a Contract object needs real ratification, not a GitHub approve-click.
---

# Ratify a HEE Contract

Real, error-prone workflow: source of truth is
`hee/skills/ratify-contract-v1.skill.yaml`. This packages that same
procedure so it's discoverable without already knowing the doctrine
file exists.

**The bug this exists to prevent:** signing a contract, then editing
it afterward (even a trivial field), invalidates the signature -- it
no longer matches the committed bytes. This bit real PRs twice
(human-execution-engine PRs #189/#190, and again in #191/#192) before
this exact ordering became a Skill.

## Trigger

A Contract object has `status: proposed` and needs real ratification
-- an authorized OPER's actual GPG signature, never a GitHub
approve-click (self-approval can't be enforced when proposer and
approver share an account) and never a majority vote.

## Prerequisites

- The signer (OPER) has a real GPG secret key; its public key is
  importable by whoever verifies later.
- The contract passes `tools/schema/validate-hee-object.py --strict`
  as `status: proposed` before starting.

## Procedure -- follow this exact order, do not reorder

1. **Stage the final content first, unsigned.** Run:
   ```
   tools/hee/ratify-contract.sh --key <gpg-key-id> --signer <name> <contract.yaml> [<contract2.yaml> ...]
   ```
   This flips `status` to `ratified` and inserts the ratification
   evidence field -- the file content is now final, but not yet
   signed.
2. **Only now, sign the final file:**
   ```
   gpg --detach-sign --armor <contract.yaml>
   ```
3. **Verify before committing anything:**
   - `sha256sum <contract.yaml>` and confirm it matches what's about
     to be committed (must be byte-identical to what was signed).
   - `gpg --verify <contract.yaml>.asc <contract.yaml>` and confirm
     "Good signature."
4. **Commit the contract and its `.asc` together, in the same commit**
   -- via `scripts/hee_git_ops.sh commit --act --reason "..."` per
   this repo's own git-mutation governance, never raw `git commit`.
5. **Never edit the contract again after signing.** Any further edit
   invalidates the signature. If a change is truly needed, the
   contract must be un-ratified and re-signed from step 1 -- there is
   no way to patch a signed file without breaking the signature.

## Post-commit verification (always, not optional)

`gpg --verify <contract>.asc <contract>` run again against the exact
committed file on the target branch -- not a local copy, not an
assumption. The failure mode here is silent: a stale signature still
parses as valid-looking armor, it just won't verify against changed
content, so re-checking after every commit that touches the file is
the only way to actually catch it.

## Real known gaps (per the source doctrine object)

- Script assumes a single OPER signer -- no N-of-M multi-party
  signature support yet.
- No automated CI check runs the post-commit verification step --
  it's still a manually-invoked discipline, not enforced.
