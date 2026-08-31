# hee-check(1)

```
hee-check -- repo boundary and integrity checks

SYNOPSIS
  hee-check [boundary] [PATH]
  hee-check refs [--fix] [PATH]
  hee-check all [PATH]
  hee-check --help

DESCRIPTION
  Checks a repository for integrity problems. PATH defaults to the current
  directory, so the tool always checks where it is invoked, never the repo
  it happens to be installed in.

  If PATH is a directory containing repositories rather than a repository
  itself (for example ~/git), every repository directly inside it is
  checked and the results are totalled. Recursion is one level deep by
  design -- descending further would crawl vendored checkouts and
  worktrees.

SUBCOMMANDS
  boundary   Derived editor state (.cursor/) must not be committed to git.
             A .cursor/ present on disk but untracked is fine and is not
             reported. Default subcommand when none is given.

  refs       Every file reference written in a doc must point at a file
             that exists. Reads .md, .yaml, .yml and .json, and inspects
             backticked and quoted paths -- not only markdown links.
             docs/history/** and hee/evidence/** are excluded: those are
             point-in-time snapshots, so a reference to a since-deleted
             file is correct history rather than rot.

  all        Run both.

OPTIONS
  --fix      refs only. Repairs a broken reference when exactly one real
             file has that basename. Ambiguous references are left alone
             for a human to decide, never guessed.

EXIT STATUS
  Nagios plugin convention.
  0  OK        no problems found
  1  WARNING   reserved
  2  CRITICAL  problems found
  3  UNKNOWN   could not determine (missing python3, unreadable path)

ENVIRONMENT
  HEE_STATUS_STYLE   icon (default), ascii, or plain. See heerc.

EXAMPLES
  hee-check                     boundary check of the current repo
  hee-check refs                every reference in the current repo
  hee-check refs ~/git          every repo under ~/git
  hee-check refs --fix          repair unambiguous references
  hee-check all ~/git/fleet-ops both checks on one repo

SEE ALSO
  hee-lint, hee-index, hee-print
```
