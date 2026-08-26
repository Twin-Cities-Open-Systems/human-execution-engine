# The HEE SOA Capsule (`hee-soa.v1`)

## What it is

A real, per-account identity file at `~/.hee/index/_.yaml`, present in every
real fleet identity's home directory on every host. It's the object that
lets you take a real thing on disk (a comment, a commit, a written file)
and trace it back to exactly which account, on which host, produced it --
the property fleet-ops#74 calls "you should be able to take any object and
trace it back to the origin."

The capsule's `hee_soa.stool_hash_full` is a real, deterministic SHA-256
value computed from three real facts about the account -- which filesystem
its home lives on, which filesystem its repo checkout lives on, and its
own username/uid/host -- via `library/py/hee_hash/soa.py`. Two capsules on
the same host that share a filesystem will always share their
`leg_home_fs`/`leg_repo_fs` hashes; only `leg_user` (and everything derived
from it) differs per-account. This is why the algorithm exists instead of
a random or self-asserted token: the hash is a real function of real,
independently-checkable facts, not a value anyone could just declare.

## When one gets created

**Every real fleet/org identity's home directory on a host gets one.**
Not just machine identities -- human OPER accounts too (see the worked
example below). Concretely, a capsule should exist:

- At account provisioning time, as part of setting up a new identity's
  home directory on a host -- the same moment you'd set up `.ssh/`,
  `.gnupg/`, or any other per-account real state.
- Retroactively, the moment the gap is found, if provisioning happened
  before this doctrine existed. Retroactive creation is not a workaround
  or a lesser version -- the resulting capsule is exactly as real and
  verifiable as one created at provisioning time, because the hash is
  computed from the account's actual current, real state either way.

There is currently no root/org-level identity file
(`owner@org:~/.hee/index/_.yaml`) that these per-host capsules chain up
to -- that's real, separate, foundational work (fleet-ops#74), not yet
done. A per-host capsule is valid and worth creating now regardless; it
"closes the loop" to the root automatically once that root exists, per
its own design -- it does not need to be redone.

## How one gets created

The real, exact process (dogfooded live, 2026-08-24, creating spencer@kiosk's
capsule as the second real one on this host, after claude@kiosk's):

1. Determine the account's real legs: `partuuid` of the filesystem backing
   `$HOME` (`findmnt -no PARTUUID /home`) for both `leg.home_fs` and
   `leg.repo_fs` (same value on a single-partition host -- most hosts in
   this fleet), and `leg.user` (`username`, `uid`, real fully-qualified
   `host`).
2. Write `~/.hee/current/soa/<hostshort>.legs.kv` in that account's own
   home directory, in the `[leg.x]` / `key=value` format
   `parse_legs_kv()` expects (see `library/py/hee_hash/soa.py`).
3. Compute the real hash chain via `SoaHasher().compute_from_legs_text()`
   -- do not hand-write or guess a hash value. It's deterministic: the
   `leg_home_fs`/`leg_repo_fs`/duople values will match another account's
   capsule on the same host/filesystem exactly; only `leg_user` and
   everything derived from it differs.
4. Write `~/.hee/current/soa/<hostshort>.hashes.txt` (the real
   intermediate values, as an audit trail) and `~/.hee/index/_.yaml` (the
   capsule itself, `hee_soa.stool_hash_full`/`stool_hash_show` from step 3).
5. `chmod 600` the `_.yaml` (owner-only -- it's a real identity artifact,
   not a shareable file) and confirm ownership matches the account, not
   whoever ran the generation.
6. Verify with the real tool, not by eye: `verify_current_host()` re-reads
   both files and recomputes the hash independently, returning `ok=True`
   only if the written `stool_hash_full` matches a fresh recomputation.

## Who creates it

Self-generation (the account generates its own capsule) is the default
and preferred path -- it matches the `verify_identity_before_writes`
invariant the capsule itself declares. A privileged peer with real sudo
(e.g. an account with `NOPASSWD:ALL`) may bootstrap a capsule on behalf of
an unprivileged account when needed -- exactly what happened for
spencer@kiosk, since `spencer@kiosk` is permanently unprivileged by design
and has no path to do this unassisted today.

## Real known gap, found while dogfooding this

`library/py/hee_hash/soa.py` -- the only real implementation of the hash
algorithm -- currently lives inside `claude`'s private git clone at
`/home/claude/git/human-execution-engine`, mode `750`. No other real
account on the host (including `spencer`) can read or import it directly;
generating a capsule for any account other than `claude` currently
requires a privileged peer running the computation as root. This works,
but it means self-generation (the preferred path, above) isn't actually
possible yet for any non-`claude` identity. Real follow-up, not solved
here: the library needs a real, world-readable home (a system path, or a
package install) independent of any one account's private clone.

## Related

- fleet-ops#74 -- the real "trace any object back to origin" doctrine this
  capsule implements
- `contracts/gcic.v1.md` -- the Agent-Sig rule (human-execution-engine#314)
  that consumes this capsule's identity for per-emission signatures
- `library/py/hee_hash/soa.py` -- the real implementation this doc
  describes the usage of, not a schema this doc redefines
