# `hee-repo-refresh` — real run

Real trigger: extracted from `bootstrap.mk`'s inline health/pull loop so
the GNU-parallel and sequential-fallback paths share one real
implementation. Extended 2026-08-29, Spencer direct: "needs switches.,
./hee repo refresh -all or -repo dotfiles, etc" then "csv of repos" —
the flag-based CLI (`all`/`-all`, `-repo <name-csv>`, and a combined
`refresh` mode) on top of the original bare-`<repo-dir>` form
`bootstrap.mk` already depended on.

Dogfooded against two real, throwaway git repos created fresh in a
temp directory (`git init`, one real commit each) — not real org
repos, so nothing here touches actual project state.

```
$ TESTROOT=$(mktemp -d)
$ export HEE_GIT_ROOT="$TESTROOT"
$ mkdir -p "$TESTROOT/repo-a" "$TESTROOT/repo-b"
$ # (git init + one commit in each; repo-b then gets one uncommitted edit)

$ hee-repo-refresh health "$TESTROOT/repo-a"
🟡 repo-a: no upstream tracking branch (master)

$ hee-repo-refresh health "$TESTROOT/repo-b"
🟠 repo-b: dirty (1 uncommitted) on master

$ hee-repo-refresh health -all
🟠 repo-b: dirty (1 uncommitted) on master
🟡 repo-a: no upstream tracking branch (master)

$ hee-repo-refresh health -repo repo-a,repo-b
🟡 repo-a: no upstream tracking branch (master)
🟠 repo-b: dirty (1 uncommitted) on master

$ hee-repo-refresh hygiene "$TESTROOT/repo-b"
repo-b: 1 uncommitted file(s), 1 branch(es) with no upstream

$ hee-repo-refresh hygiene "$TESTROOT/repo-a"
repo-a: 0 uncommitted file(s), 1 branch(es) with no upstream

$ hee-repo-refresh bogus "$TESTROOT/repo-a"
hee-repo-refresh: unknown mode 'bogus' (want health|pull|hygiene|refresh)
$ echo $?
2
```

All real exit codes: `0` for every recognized mode regardless of
health color (color is informational, not a failure signal), `2` for
an unrecognized mode.

## Real correction to the tool's own header comment

The header comment claims `hygiene` "prints nothing at all for a clean
repo." That's real but incomplete: it's silent only when *both*
real conditions are zero (0 uncommitted files **and** 0 branches with
no upstream) — a freshly-`git init`'d repo like `repo-a` above has a
real local branch with no upstream by construction, so it reports that,
correctly, rather than staying silent. Not a bug; the doc comment
should say "clean *and fully tracked*" repo, not just "clean."

## Not verified in this fixture

- The `refresh` mode's real governance-reminder print (calls
  `make -f bootstrap.mk print-governance-reminder`) — not exercised
  here since these throwaway repos aren't inside a real checkout of
  `human-execution-engine` with a real `bootstrap.mk` alongside them.
- `pull` mode against a repo with a real configured remote — the
  throwaway repos here have no remote, so `pull` isn't meaningfully
  testable against them; would need a second local bare repo acting as
  a real remote to test this properly. Not built here.
- GNU-parallel vs. sequential-fallback dispatch for `-all`/`-repo`
  scopes — both real paths exist in the source but weren't
  independently confirmed to produce identical output in this pass
  (the sequential path was what actually ran, since the real
  parallel/sequential choice depends on `command -v parallel` in this
  environment).
