# `hee-scan` — real run

Real trigger: "./hee -scan storage -r 'hygien|foo|bar{3,}' # only valid
regex ever, our 1 true regex" -- generalizes the ad-hoc `rg` calls run
by hand tonight into a real tool, standardized on ripgrep's own regex
dialect everywhere (same choice `hee-srtscan` already made).

```
$ hee-scan -target storage -r 'hygien|foo|bar{3,}'
/mnt/nuc1-pool/storage/docs/.../IMPLEMENTATION_MANUAL-partial.md:85: ...footprint...
/mnt/nuc1-pool/storage/docs/shared/20260814T174623Z-touchy-pre-reinstall-inventory.txt:205: foomatic-db-compressed-ppds			install
...
```

Real alternation confirmed working correctly -- "footprint" matches
because it contains the literal substring "foo", not a bug.

Real, same-session finding this tool also has to handle: mixed file
ownership means some files under `storage`/`media` aren't readable by
this account. `rg` reports that on stderr and returns a non-0/1 exit
even when other real matches came through fine -- `hee-scan` treats
that as non-fatal and reports a real skipped-file count instead of
aborting the whole scan.

## Explicitly not built here

- Only two named targets (`storage`, `media`) -- real, not exhaustive;
  add more as they come up, not speculatively.
- No caching -- same real NFS-walk cost as `hee-srtscan`, not solved
  here either.
