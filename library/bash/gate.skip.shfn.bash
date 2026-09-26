# gate.skip.shfn.bash -- read a repo's own declared hee-check exemptions.
#
# A repo declares its exemptions (HEE_REFS_SKIP, HEE_HOME_PATH_SKIP,
# HEE_LINT_SKIP) as env values in its .github/workflows, where CI sets them
# before calling hee-check. A LOCAL run got none of that, so `hee check all`
# in fleet-ops reported CRITICALs its own CI would never raise -- measured
# 2026-09-26: 30 false CRITICAL refs under pve/agents/jobs, all of which the
# workflow's HEE_REFS_SKIP exempts. The exemptions are a property of the
# repo, not of who is standing in it.
#
# This was born inside hee-repo-refresh as a private _gate_skip; rule 15 --
# one implementation, in library/, where both the gate and hee-check itself
# read a repo's exemptions the same way.
#
# POSIX sh. Needs `rg`; without it, echoes nothing (callers then keep their
# own default, which is the pre-replay behaviour -- no worse than before).

# hee_gate_skip VAR DIR -- echo the value declared for VAR in DIR's workflows.
#
# Strips the YAML double quotes and NOTHING ELSE. The single quotes inside are
# load-bearing: hee-check evals these pathspecs (`eval git -C ... $_HP_SKIP`),
# so ':!hosts/*' must keep its quotes or the pathspec is never applied.
# Measured 2026-09-07 -- stripping them turned fleet-ops from 0 findings into 20.
#
# --no-filename matters too: scanning a DIRECTORY makes rg prefix every hit
# with its path, which corrupts the value and hides the leading quote from the
# strip. Measured, not guessed.
hee_gate_skip() {
  _hgs_var="$1"
  _hgs_dir="$2"
  command -v rg >/dev/null 2>&1 || return 0
  [ -d "$_hgs_dir/.github/workflows" ] || return 0
  _hgs_val="$(rg --no-filename --no-line-number -o -m1 \
     "^[[:space:]]*$_hgs_var:[[:space:]]*(.*)$" -r '$1' \
     "$_hgs_dir/.github/workflows" 2>/dev/null | head -1 \
     | sed -e 's/^"//' -e 's/"$//')"
  # A GitHub Actions template (`${{ matrix.refs_skip }}`) is a reference to a
  # value defined elsewhere in the workflow, not the value itself -- this is
  # what hee's OWN stable.yaml carries for its consumer matrix. Replaying the
  # literal is meaningless (it matches no directory) and misleading, so drop
  # it. A repo that pins a real literal skip (fleet-ops does) is unaffected.
  # shellcheck disable=SC2016  # literal '${{' is the point -- no expansion wanted
  case "$_hgs_val" in
    *'${{'*) return 0 ;;
  esac
  printf '%s\n' "$_hgs_val"
}
