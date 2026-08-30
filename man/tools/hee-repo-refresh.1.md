# hee-repo-refresh(1)

hee-repo-refresh -- real per-repo health-check/pull worker for
bootstrap.mk's health-all-repos and pull-all-repos targets. Extracted
into its own script, rather than embedded inline in the Makefile
recipe twice, so the GNU-parallel path and the sequential fallback
path call the exact same real logic instead of two copies that can
silently drift -- HEE#415, Spencer direct 2026-08-28: "add gnu
parallel to this tool." Real trigger for parallelizing at all: with
~19-24 real repos each doing a real git fetch/pull over the network,
the old one-at-a-time loop was a real, avoidable wall-clock cost,
confirmed live refreshing both claude@kiosk and spencer@kiosk.

Deliberately its own script (not a Makefile-only trick) so it can be
invoked identically two ways: `parallel hee-repo-refresh health ::: $repos`
(concurrent) or a plain `for d in $repos; do hee-repo-refresh health "$d"; done`
(sequential fallback when GNU parallel isn't installed) -- bootstrap.mk
picks whichever via `command -v parallel`.

Usage:
  hee-repo-refresh <health|pull|hygiene|refresh> <repo-dir>
  hee-repo-refresh <health|pull|hygiene|refresh> [all|-all]
  hee-repo-refresh <health|pull|hygiene|refresh> -repo <name>[,<name>...]

The bare <repo-dir> positional form (a real filesystem path) is what
bootstrap.mk's own health-all-repos/pull-all-repos targets pass
internally -- kept exactly as-is, never break that. `all`/`-all` (both
accepted) and `-repo <name-csv>` are the real, human-facing entry
points added 2026-08-29, Spencer direct: "needs switches., ./hee repo
refresh -all or -repo dotfiles, etc" then "csv of repos" -- -repo
takes real repo *names* (dotfiles, not /home/x/git/dotfiles),
resolved under ${HEE_GIT_ROOT:-$HOME/git}, comma-separated for more
than one.

health/pull print one real 🟢/🟡/🟠/🔴-prefixed line to stdout -- same
format the old inline Makefile loop produced, byte-for-byte, so
parallel output (each job's single line prints atomically, GNU
parallel's own default --group behavior) reads exactly the way the
sequential output always did. hygiene (added for
fleet-ops/hosts/spencer/bin/hee-git-hygiene-report.sh's real,
distinct check -- dirty-file-count + no-upstream-branch-count across
ALL local branches, not just the current one) prints nothing at all
for a clean repo, matching that script's original silent-unless-a-
problem behavior exactly. refresh (added 2026-08-29, Spencer direct:
"hee repo refresh I think for now" -- a single real command instead
of two-plus-a-Makefile-target) runs the exact same real sequence as
bootstrap.mk's refresh-all-repos: a full health pass, then a full
pull pass, then the governance reminder -- printed once per real
invocation of a scope (all/-all/-repo), not once per repo inside it.
Only the bare <repo-dir> positional form (a real filesystem path --
what bootstrap.mk's own targets pass internally) skips the reminder
entirely, since that form is always one worker among many others
already fanned out by something else, never the whole real scope.

*(no --help/-h output -- generated from the script's own header comment)*
