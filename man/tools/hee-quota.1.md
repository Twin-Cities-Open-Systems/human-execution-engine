# hee-quota(1)

```
usage: hee-quota [-h] {status,warn,wait} ...

hee-quota: monitor GitHub API rate-limit pools (core/graphql/search) and
give a real, live go/no-go before a bulk operation, instead of finding out
reactively mid-batch.

Real trigger: hit GraphQL exhausted (0/5000, then again at 81/5000) twice
in one session while core REST stayed near-full both times -- confirmed via
`gh api rate_limit` only *after* a batch had already failed partway
through. This is the pre-flight check that should have run first.

Checking rate_limit itself does not consume quota (confirmed live) --
safe to call before every bulk run, not just when something's already
gone wrong.

Usage:
  hee-quota status              -- print remaining/limit/reset per pool
  hee-quota status --json       -- machine-readable
  hee-quota warn [--threshold N]  -- exit 1 if any pool is below N% remaining
                                     (default 20), otherwise exit 0 silently.
                                     Use as a real pre-flight gate:
                                       hee-quota warn --threshold 15 || exit 1
  hee-quota wait --pool graphql --min N
                                 -- block (with backoff) until the named
                                    pool has at least N remaining, then
                                    exit 0. Real ETA printed from the
                                    pool's own reset timestamp, not guessed.

positional arguments:
  {status,warn,wait}

options:
  -h, --help          show this help message and exit
```
