# repo.config.shfn.bash -- a repo's own hee settings, read from .hee/config.yaml.
#
# The checks accept per-repo exemptions (HEE_REFS_SKIP, HEE_HOME_PATH_SKIP,
# HEE_LINT_SKIP), and until 2026-09-18 the only place a repo could put them
# was its CI workflow's `env:` block. So CI read the repo's declaration and
# a local `hee check all` did not: fleet-ops was green on GitHub and red on
# every laptop, on the same tree (fleet-ops ticket 0067). A declaration the
# checker only sees in one of its two homes is not a declaration.
#
# The repo says it once, here, and every runner reads it:
#
#     check:
#       refs_skip:            # directories whose references are not canonical
#         - viz-dashboard/public
#       home_path_skip:       # git pathspecs the home-path scan skips
#         - ':!pve/agents/jobs/*/in/*'
#       lint_skip:            # git pathspecs hee-lint skips
#         - ':!viz-dashboard/public/*'
#
# The environment variables still work and are appended AFTER the file, so
# a one-off run can widen a skip and never silently narrow one.
#
# Deliberately a flat awk reader, not a YAML parser: the block is three
# keys of plain lists, python3 and pyyaml are not a given on every host
# hee-check runs on, and a checker that needs a library to learn what to
# skip is a checker that skips nothing when the library is missing.
#
# Usage:
#     . "$TOOL_ROOT/library/bash/repo.config.shfn.bash"
#     hee_repo_config_list "$root" refs_skip     # one item per line, or nothing

hee_repo_config_list() {
  _cfg="${1:-.}/.hee/config.yaml"
  _key="${2:?hee_repo_config_list: key required}"
  [ -r "$_cfg" ] || return 0
  awk -v key="$_key" '
    # top-level `check:` opens the block; any other top-level key closes it
    /^[^ #][^:]*:/       { inblock = ($0 ~ /^check:/); inkey = 0; next }
    !inblock             { next }
    /^  [A-Za-z_]+:/     { sub(/^  /, ""); sub(/:.*/, ""); inkey = ($0 == key); next }
    inkey && /^    - /   {
      sub(/^    - */, ""); sub(/[ \t]*(#.*)?$/, "")
      gsub(/^["'\'']|["'\'']$/, "")
      if (length($0)) print
    }
  ' "$_cfg"
}
