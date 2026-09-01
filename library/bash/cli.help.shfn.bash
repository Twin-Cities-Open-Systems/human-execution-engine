# cli.help.shfn.bash -- uniform `help` handling for every hee tool.
#
# THE RULE, operator 2026-08-31: "make sure help works everywhere and when
# found, does help on prev verb/etc and not exec anything to right".
#
# Three properties, in order of how much they cost when violated:
#
#  1. `help`, `--help` and `-h` all work, from ANY position in argv.
#  2. Help is for the verb chain to the LEFT of the help token, so
#     `hee check refs help` documents `refs`, not `check`.
#  3. NOTHING TO THE RIGHT OF THE HELP TOKEN IS EXECUTED. This is the
#     safety property. A tool that scans only $1, or only the LAST
#     argument, will happily run `hee repo-refresh help --force` as a
#     real --force. Asking for help must never be able to do anything.
#
# Property 3 is why this cannot be `case "$1"` and cannot be the `_last`
# idiom several tools currently use -- both are positional, and the help
# token can be anywhere.
#
# Usage in a tool:
#
#     . "$TOOL_ROOT/library/bash/cli.help.shfn.bash"
#     if hee_help_wanted "$@"; then
#       hee_help_verbs "$@" | read -r chain   # verbs left of the token
#       usage_for "$chain"; exit 0
#     fi
#
# NOT MIRRORED HERE, deliberately: the Python sibling (library/py/hee_cli)
# takes a `value_flags` argument, so a token after a value-taking flag is that
# flag's VALUE rather than a help request -- `hee-stat -c help` names a
# counter called "help". Two Python tools need it. No shell tool does, and
# writing the shell half before anything calls it would be speculative code
# that nothing proves. Add it here the day a shell tool takes a flag whose
# value could be the word "help", and say so in both files.
#
# POSIX sh -- no bashisms, per rule 6 and the org's all-POSIX shell rule.

# True if any argument is a help token. Scans the WHOLE argv, not $1.
hee_help_wanted() {
  for _a in "$@"; do
    case "$_a" in
      help|--help|-h) return 0 ;;
      # `--` ends option parsing; a `help` after it is a literal operand,
      # not a request for help. Respecting this keeps `hee print -- help`
      # meaning "print the word help".
      --) return 1 ;;
    esac
  done
  return 1
}

# Echo everything strictly to the LEFT of the first help token, unfiltered,
# space-separated. Everything from the token rightward is deliberately
# discarded -- that is property 3, and discarding it here is what makes it
# impossible to run.
#
# Flags are KEPT, unlike hee_help_verbs, because some tools spell their
# actions as flags: `hee-ticket -close help` must resolve to the -close page,
# and a verbs-only view cannot see it.
hee_help_left() {
  _out=""
  for _a in "$@"; do
    case "$_a" in
      help|--help|-h) break ;;
      --) break ;;
      *) _out="${_out:+$_out }$_a" ;;
    esac
  done
  printf '%s\n' "$_out"
}

# Echo the verb chain to the LEFT of the first help token, space-separated.
# Flags are not verbs and are skipped -- use hee_help_left when a tool's
# actions are spelled as flags.
hee_help_verbs() {
  _out=""
  for _a in "$@"; do
    case "$_a" in
      help|--help|-h) break ;;
      --) break ;;
      -*) continue ;;   # flags are not verbs
      *) _out="${_out:+$_out }$_a" ;;
    esac
  done
  printf '%s\n' "$_out"
}

# The deepest verb -- what a tool usually dispatches its usage_* on.
hee_help_topic() {
  _chain="$(hee_help_verbs "$@")"
  printf '%s\n' "${_chain##* }"
}

# Echo what was to the RIGHT of the help token -- the part that was NOT run.
hee_help_ignored() {
  _seen=0; _out=""
  for _a in "$@"; do
    if [ "$_seen" = 1 ]; then _out="${_out:+$_out }$_a"; continue; fi
    case "$_a" in help|--help|-h) _seen=1 ;; esac
  done
  printf '%s\n' "$_out"
}

# Tell the operator, on stderr, that the rest of the line was discarded.
#
# Operator, 2026-08-31, on seeing the discard proved in a table: "add that
# to the output, check that in future". Silence here is the failure mode --
# someone types `hee repo-refresh help --force`, gets a help page, and has
# no way to know whether --force ran. Saying so converts an invisible
# safety property into a visible one.
#
# stderr, not stdout, so `hee foo help | ...` still pipes clean help text.
hee_help_note_ignored() {
  _ig="$(hee_help_ignored "$@")"
  [ -z "$_ig" ] && return 0
  printf 'ℹ️  NOTE  not executed (right of the help token): %s\n' "$_ig" >&2
}
