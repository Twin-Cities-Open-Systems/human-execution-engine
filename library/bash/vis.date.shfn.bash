# vis.date.shfn.bash -- time shown to a person, the way that person's `date` shows it.
#
# section: 3
#
# Operator, 2026-09-11: "if I change my settings to default to another iso
# type, our tools (all) should report time in the same format as the current
# user". So `date` does the formatting, at call time, with the caller's TZ,
# LC_TIME, LC_ALL and LANG. $HEE_DATE_FORMAT, set in heerc, overrides the shape
# for every hee tool at once, as a `date` format such as %F %T %Z.
#
# Display only. Records, cursors, JSON and committed files keep ISO-8601 UTC:
# a locale-shaped stamp would make the same file differ from machine to machine.
#
# Parity: library/py/hee_day local_dates prints the same thing for the same
# input, checked by tests/test_hee_date_parity.py.
#
# USAGE
#   . "$TOOL_ROOT/library/bash/vis.date.shfn.bash"
#   hee_date 2026-09-11T19:47:37Z          # Fri Sep 11 02:47:37 PM CDT 2026
#   hee_date @1789156057 "$started_at"     # one line per stamp
#
# A value that is not a timestamp with a time of day (ISO-8601 or @epoch)
# prints unchanged, as does one `date` cannot read. A stamp with no zone is UTC.

hee_date() {
  for _hd_s in "$@"; do
    case "$_hd_s" in
      @[0-9]*) _hd_in="$_hd_s" ;;
      [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][T\ ][0-9][0-9]:[0-9][0-9]*)
        case "$_hd_s" in
          *Z|*[+-][0-9][0-9]:[0-9][0-9]|*[+-][0-9][0-9][0-9][0-9]) _hd_in="$_hd_s" ;;
          *) _hd_in="${_hd_s}Z" ;;
        esac ;;
      *) printf '%s\n' "$_hd_s"; continue ;;
    esac
    if [ -n "${HEE_DATE_FORMAT:-}" ]; then
      _hd_out="$(date -d "$_hd_in" "+${HEE_DATE_FORMAT#+}" 2>/dev/null)"
    else
      _hd_out="$(date -d "$_hd_in" 2>/dev/null)"
    fi
    printf '%s\n' "${_hd_out:-$_hd_s}"
  done
}
