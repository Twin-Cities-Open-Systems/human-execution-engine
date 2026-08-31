# vis.status.shfn.bash
# stage: ~/.hee/library/bash/
# PURPOSE: one canonical status vocabulary for every HEE tool's output.
#
# DOC (md-compat):
#   - . ~/.hee/library/bash/vis.status.shfn.bash
#   - hee_status <OK|WARNING|CRITICAL|UNKNOWN> <msg>  -> one status line
#   - hee_status_code <LEVEL>                         -> Nagios exit code
#   - hee_status_demo                                 -> preview current style
#
# WHY NAGIOS:
#   OK / WARNING / CRITICAL / UNKNOWN with exit codes 0/1/2/3 is the
#   Nagios plugin API -- a real, forty-year-old standard, already the
#   framing used in docs/specs/HEE_HARDWARE_DISCOVERY.md. Adopted rather
#   than invented, per the org's no-wheel-reinvention preference.
#
#   It also fixes a real rule 11 defect at the API level: the older
#   `vis_flag` took `green|yellow|red` -- the caller named a *hue*, not a
#   severity. Colour was the semantics. Here the caller names severity and
#   presentation is a downstream, user-configurable concern.
#
# RULE 11 COMPLIANCE:
#   Every line ships an icon AND a text label, never colour alone, and the
#   icons are shape-distinct (check / triangle / cross / question) rather
#   than three identical circles differing only in hue -- which is what
#   made the old 🔴🟡🟢 output unreadable on a daltonized theme even
#   though it was technically "coloured correctly".
#
# STYLE (user preference -- set in heerc, or per-shell):
#   HEE_STATUS_STYLE=icon    ✅ OK      message      (default)
#   HEE_STATUS_STYLE=ascii   [OK]       message      (pipes, logs, no-emoji terms)
#   HEE_STATUS_STYLE=plain   OK         message      (machine-ish, no decoration)
#
# MACHINE PARSING:
#   Parse the LABEL, never the icon. The icon is presentation and is
#   expected to change; the label is the contract. (Real regression this
#   prevents: hee-index parsed hee-lint's emoji as its status field, which
#   froze the icons until it was decoupled 2026-08-31.)

hee_status__level() {
  # normalise: accept lowercase, and the legacy colour words
  case "$(printf '%s' "${1:-}" | tr '[:lower:]' '[:upper:]')" in
    OK|GREEN)              printf 'OK' ;;
    WARN|WARNING|YELLOW)   printf 'WARNING' ;;
    CRIT|CRITICAL|ERROR|RED) printf 'CRITICAL' ;;
    *)                     printf 'UNKNOWN' ;;
  esac
}

hee_status_code() {
  case "$(hee_status__level "${1:-}")" in
    OK)       return 0 ;;
    WARNING)  return 1 ;;
    CRITICAL) return 2 ;;
    *)        return 3 ;;
  esac
}

hee_status__icon() {
  case "${1}" in
    OK)       printf '✅' ;;
    WARNING)  printf '⚠️' ;;
    CRITICAL) printf '❌' ;;
    *)        printf '❓' ;;
  esac
}

hee_status() {
  _lvl="$(hee_status__level "${1:-}")"
  shift 2>/dev/null || true
  _msg="$*"
  [ -n "$_msg" ] || _msg="(no message)"

  case "${HEE_STATUS_STYLE:-icon}" in
    plain) printf '%s %s\n' "$_lvl" "$_msg" ;;
    ascii)
      case "$_lvl" in
        OK)       printf '[OK]   %s\n' "$_msg" ;;
        WARNING)  printf '[WARN] %s\n' "$_msg" ;;
        CRITICAL) printf '[CRIT] %s\n' "$_msg" ;;
        *)        printf '[UNKN] %s\n' "$_msg" ;;
      esac
      ;;
    *) printf '%s %s %s\n' "$(hee_status__icon "$_lvl")" "$_lvl" "$_msg" ;;
  esac
}

hee_status_demo() {
  printf 'HEE_STATUS_STYLE=%s\n\n' "${HEE_STATUS_STYLE:-icon (default)}"
  hee_status OK       "everything is fine"
  hee_status WARNING  "something needs a look"
  hee_status CRITICAL "something is broken"
  hee_status UNKNOWN  "could not determine state"
  printf '\nOther styles: icon | ascii | plain  (set HEE_STATUS_STYLE in your heerc)\n'
}
