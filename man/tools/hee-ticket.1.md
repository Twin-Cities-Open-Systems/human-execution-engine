# hee-ticket(1)

```
hee-ticket -- repo-local tickets, stored as real YAML in git

SYNOPSIS
  hee-ticket -new "DESCRIPTION"
  hee-ticket -list
  hee-ticket -advance ID
  hee-ticket -close SPEC
  hee-ticket [-ACTION] help

DESCRIPTION
  The smallest real, dogfoodable step toward tracking that TCOS owns
  outright, rather than renting from GitHub Issues. It does not replace
  GitHub Issues and does not sync with them -- nothing here reaches the
  network at all.

  Storage is one file per ticket at .hee/tickets/<id>.yaml under the
  repo root of the CURRENT directory, so which repo you are standing in
  decides which ticket set you are looking at. The files are ordinary
  tracked YAML: commit them like anything else, and read or edit them by
  hand when this tool cannot express what you need.

  Every ticket carries the real idea -> footgun -> dogfood pipeline as a
  structural `stage` field plus a `stage_history` of timestamped
  transitions -- so stage counts and durations are derived from record,
  never asserted.

ACTIONS
  -new       open a ticket at stage idea
  -list      print every ticket in this repo
  -advance   move one ticket one stage forward
  -close     close tickets by id, range, or description regex

  Exactly one action runs per invocation. If several are passed they are
  tested in the order above and the first one present wins; the rest are
  silently ignored rather than rejected.

  Add `help` after any action for its own page:
      hee-ticket -close help

EXIT STATUS
  Nagios plugin convention.
  0 OK        the action completed
  1 WARNING   no action given (this page is printed), not inside a git
              repo, pyyaml missing, or the action's own failure -- see
              each action's page. Note: several of these are UNKNOWN- or
              CRITICAL-shaped in the org vocabulary; the tool really
              exits 1 today and is documented as-is, not changed here.

ENVIRONMENT
  No environment variables are read. `git` must be on PATH, the current
  directory must be inside a git repo, and pyyaml must be importable.

FILES
  .hee/tickets/<id>.yaml   one record per ticket, under the repo root

SEE ALSO
  hee-git-merge -- shares the same id/range/regex selector
  (library/py/hee_range)
```
