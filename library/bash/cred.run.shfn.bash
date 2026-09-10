# cred.run.shfn.bash
# stage: ~/.hee/library/bash/
# PURPOSE: run a command with a sealed credential in its environment, and
#          nowhere else -- no temp file, no export into the caller's shell.
#
# DOC (md-compat):
#   - . ~/.hee/library/bash/cred.run.shfn.bash
#   - hee_cred_run <account> <cmd...>            -> cmd sees the derived var
#   - hee_cred_run_as <VAR> <account> <cmd...>   -> cmd sees $VAR
#   - hee_cred_export <account> [VAR]            -> prints `VAR=...` for eval
#
# WHY THIS EXISTS:
#   A child process cannot set its parent's environment. That is an OS
#   boundary, not a tooling gap, so "put the token in $PLEX_TOKEN" has
#   exactly two honest shapes: run the consumer as a child with the
#   variable set, or eval an assignment into the current shell. Every tool
#   in this org was open-coding the first one as
#
#     hee cred -pass plex-token -exec sh -c 'PLEX_TOKEN="$HEE_CRED_PASS" exec "$@"' _ cmd
#
#   which is easy to get wrong in a way that FAILS QUIETLY -- see the dash
#   note below. `hee cred -run` now does the injection itself; these
#   functions are the shell-side ergonomics on top of it.
#
# THE DASH TRAP (measured 2026-09-09):
#   The obvious eval form uses printf %q to quote the secret safely:
#
#     eval "$(hee cred -pass X -exec sh -c 'printf "V=%q\n" "$HEE_CRED_PASS"')"
#
#   On Debian /bin/sh is dash, whose printf has NO %q. It emits an error to
#   stderr, the command substitution yields nothing, eval runs nothing, and
#   the variable is silently EMPTY. The caller then debugs the wrong layer,
#   because an empty credential looks like a decrypt problem. So
#   hee_cred_export forces bash for that one step, deliberately.
#
# WHICH ONE TO USE:
#   hee_cred_run       -- default. The secret lives in one short-lived
#                         process and dies with it.
#   hee_cred_export    -- only for interactive poking. The secret lands in
#                         the shell's environment, is readable through
#                         /proc/<pid>/environ by any same-user process, and
#                         is inherited by EVERY later command in that shell
#                         -- including anything that logs its own env.
#                         `unset` it when done.

hee_cred__hee() {
  # The dispatcher, not an absolute path -- per the org's no-baked-paths
  # rule. Falls back to the tool directly if `hee` is not on PATH, which is
  # the normal case inside a non-login shell.
  if command -v hee >/dev/null 2>&1; then echo hee; else echo hee-cred; fi
}

hee_cred_run() {
  if [ "$#" -lt 2 ]; then
    echo "hee_cred_run: usage: hee_cred_run <account> <cmd...>" >&2
    return 3
  fi
  _hcr_acct="$1"; shift
  if [ "$(hee_cred__hee)" = "hee" ]; then
    hee cred -run "$_hcr_acct" -exec "$@"
  else
    hee-cred -run "$_hcr_acct" -exec "$@"
  fi
}

hee_cred_run_as() {
  if [ "$#" -lt 3 ]; then
    echo "hee_cred_run_as: usage: hee_cred_run_as <VAR> <account> <cmd...>" >&2
    return 3
  fi
  _hcr_var="$1"; _hcr_acct="$2"; shift 2
  if [ "$(hee_cred__hee)" = "hee" ]; then
    hee cred -run "$_hcr_acct" -as "$_hcr_var" -exec "$@"
  else
    hee-cred -run "$_hcr_acct" -as "$_hcr_var" -exec "$@"
  fi
}

hee_cred_export() {
  # Prints one `VAR=<quoted>` line for the caller to eval. Prints NOTHING on
  # failure, so `eval "$(hee_cred_export ...)"` cannot half-apply.
  if [ "$#" -lt 1 ]; then
    echo "hee_cred_export: usage: eval \"\$(hee_cred_export <account> [VAR])\"" >&2
    return 3
  fi
  _hce_acct="$1"; _hce_var="${2:-}"
  if [ -n "$_hce_var" ]; then
    # shellcheck disable=SC2016  # deliberate: expands in the CHILD bash, not here
    hee cred -run "$_hce_acct" -as "$_hce_var" \
      -exec bash -c 'printf "%s=%q\n" "$0" "${!0}"' "$_hce_var"
  else
    # shellcheck disable=SC2016  # deliberate: expands in the CHILD bash, not here
    hee cred -run "$_hce_acct" \
      -exec bash -c 'v=$(printf %s "$0" | tr "a-z-" "A-Z_"); printf "%s=%q\n" "$v" "${!v}"' "$_hce_acct"
  fi
}
