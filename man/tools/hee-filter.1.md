# hee-filter(1)

```
hee-filter -- the shared publish-safety gate

SYNOPSIS
  hee-filter check-repo OWNER/REPO
  hee-filter prime-repos [ORG]
  hee-filter scan [--i-reviewed-manually]
  hee-filter check-mode REQUESTED --venue NAME --supported a,b,c
  hee-filter [SUBCOMMAND] help

DESCRIPTION
  One implementation of the checks that must run before anything is
  published, per contracts/publish-sanitization-v1.contract.yaml, so a
  second consumer calls this tool instead of growing a second copy of
  the logic. It exists because exactly that happened: the visibility
  filter and content scan were built inline in hee-publish and were then
  found missing from tcos-www's generator.

  Every subcommand is a gate, and every gate FAILS CLOSED -- an
  unanswerable question is answered "not safe", never "probably fine".

SUBCOMMANDS
  check-repo    confirm a repo is really public (live, cached 60s)
  prime-repos   warm that cache for a whole org in one call
  scan          run tcos-audit's ruleset over content on stdin
  check-mode    pick the safe language-profile mode for a venue

  Add `help` after any subcommand for its own page:
      hee-filter scan help

EXIT STATUS
  Nagios plugin convention.
  0 OK        the gate passed
  1 WARNING   the gate did not pass -- private repo, or real findings
  2 CRITICAL  the gate could not run -- missing/unknown subcommand, wrong
              arguments, or the scanner is unavailable

ENVIRONMENT
  HOME   locates the 60s visibility cache at
         ~/.config/hee/cache/repo-visibility/ and the scanner at
         ~/git/tcos-audit/bin/scan_common.py. Neither path is
         configurable today.

  `gh` must be installed and authenticated for check-repo and
  prime-repos. Whatever gh honours (GH_TOKEN, GH_HOST) applies to them.

SEE ALSO
  hee-publish -- the first consumer
  contracts/publish-sanitization-v1.contract.yaml
```
