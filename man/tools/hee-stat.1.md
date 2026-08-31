# hee-stat(1)

```
hee-stat -- stat(1)'s -c FORMAT convention over namespaced resources

SYNOPSIS
  hee-stat -c FORMAT gh/OWNER
  hee-stat -c FORMAT gh/OWNER/REPO
  hee-stat help

DESCRIPTION
  Prints one line: FORMAT with every %SPECIFIER replaced by the real
  value read from the resource. Not a fork of GNU coreutils' stat -- the
  same familiar interface applied to a namespaced path instead of a
  filesystem path.

  Only the gh/ namespace exists. A path with one component after gh/ is
  a GitHub user or org; two components is a repo. Three or more is an
  error, not a deeper lookup. Data comes from `gh api`, so gh must be
  installed and authenticated, and private resources resolve only if
  that token can see them.

FORMAT SPECIFIERS
  Real stat(1) semantics, reused where they map:
    %n   name -- OWNER, or OWNER/REPO
    %U   owner/org login
    %W   creation time, stat's "birth time" -- created_at as Unix epoch
    %Y   last-updated time, stat's "mtime" -- pushed_at for a repo
         (falling back to updated_at), updated_at for a user
    %s   size -- repo size in KB, or a user's public repo count
  Convenience aliases:
    %REPO   repo name; empty string for a user path
    %ORG    owner/org login, alias of %U

  Footgun, real: a specifier greedily consumes every letter that follows
  it, so "%Ufoo" is read as the unknown specifier %Ufoo and errors out
  rather than expanding %U. Put a non-letter after single-letter
  specifiers -- "%U/%REPO" and "%U %n" are fine.

  Times are printed as bare Unix epoch seconds, never formatted -- pipe
  through `date -d @<n>` if you want a human date.

EXIT STATUS
  Nagios plugin convention.
  0 OK        the formatted line was printed
  1 WARNING   `gh api` failed or returned non-JSON, the namespace was not
              gh/, the path was too deep, or FORMAT used an unknown
              specifier -- message on stderr. Note: the org vocabulary
              would put these at 2 CRITICAL / 3 UNKNOWN; the tool really
              exits 1 today and is documented as-is, not changed here.
  2 CRITICAL  argparse usage error -- -c or the path was missing

ENVIRONMENT
  No environment variables are read directly. `gh` is invoked as a
  subprocess, so whatever gh itself honours (GH_TOKEN, GH_HOST, and the
  gh config) applies to the lookups.

EXAMPLES
  hee-stat -c %REPO gh/spencerbutler/human-execution-engine
  hee-stat -c '%U/%REPO %s KB' gh/Twin-Cities-Open-Systems/hee
  hee-stat -c %W gh/spencerbutler
```
