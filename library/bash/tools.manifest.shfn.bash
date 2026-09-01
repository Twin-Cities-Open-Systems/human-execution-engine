# tools.manifest.shfn.bash -- reading tooling/tools.manifest.txt, once.
#
# The manifest is read by two tools that must agree: hee-tools-check (the
# read-only half) and hee-tools-update (the mutating half). They did not
# agree. hee-tools-check grew a resolver that understands the name field;
# hee-tools-update kept matching literal names in a case statement, so
# 2 of 8 entries fell through to "unknown manifest entry" and were never
# acted on -- including `bat|batcat`, the manifest's only `required` line.
#
# Measured 2026-09-01, from a real run (issue 507):
#
#     ⚠️ WARNING unknown manifest entry: bat|batcat pkg any
#     ⚠️ WARNING unknown manifest entry: smilint pkg any
#
# Requiredness that is never evaluated is worse than a red check: it reads
# as enforcement and enforces nothing.
#
# So the shared half lives here, and neither tool keeps its own copy. Rule
# 15 -- one implementation, in library/, where it is testable and reusable.
#
# POSIX sh -- no bashisms, per rule 6 and the org's all-POSIX shell rule.

# hee_manifest_resolve_tool SPEC -- echo the first alternate present on PATH.
#
# The manifest's NAME field may list alternates as `name|alt1|alt2`, first
# one present wins.
#
# Real case: Debian and Ubuntu ship bat as `batcat`, because `bat` collides
# with bacula-console-qt. So `apt install bat` produces /usr/bin/batcat and
# NO `bat`, and a manifest naming only `bat` reports "missing" on a machine
# where the tool is installed and working. hee-print already resolves this
# in pick_bat(); the manifest needed the same understanding.
#
# Returns 1 and echoes nothing when no alternate is present.
hee_manifest_resolve_tool() {
  _hmrt_spec="$1"
  _hmrt_old_ifs="$IFS"; IFS='|'
  for _hmrt_cand in $_hmrt_spec; do
    if command -v "$_hmrt_cand" >/dev/null 2>&1; then
      IFS="$_hmrt_old_ifs"
      printf '%s\n' "$_hmrt_cand"
      return 0
    fi
  done
  IFS="$_hmrt_old_ifs"
  return 1
}

# hee_manifest_primary SPEC -- the first alternate, present or not.
#
# What to name in a "missing" message and an apt hint: `bat|batcat` should
# suggest `apt install bat`, not `apt install bat|batcat`.
hee_manifest_primary() {
  printf '%s\n' "${1%%|*}"
}
