# cards.scan.shfn.bash
#
# shfn: fast, tolerant inventory of hee/cards/* using rg_scan/rg_count
# (see rg.scan.shfn.bash). Incubating stage of the shfn -> sh -> bash ->
# py -> go graduation pipeline (uiboss-repohub-next.wip.yaml) --
# tooling/bin/scan-hee-cards.py is the already-graduated py stage,
# for the one thing pure grep genuinely can't do well: freeform
# `status:` values that are themselves nested YAML (not a string).
#
# Why this exists: the cards dir is NOT homogeneous -- kind: Card,
# kind: Pill, plain .md docs, and detached .asc PGP signatures that
# happen to end in .yaml all live side by side. This never assumes a
# single shape; every check here is a count, never a parse that can
# blow up on the wrong file.
#
# Requires: rg.scan.shfn.bash sourced first (rg_count).
#
# Usage:
#   cards_scan [dir]   # defaults to hee/cards

cards_scan() {
  local dir="${1:-hee/cards}"
  if [ ! -d "$dir" ]; then
    echo "❌ cards_scan: no such dir: $dir" >&2
    return 2
  fi

  local total card_n pill_n md_n asc_n other_yaml_n needs_dif_n
  total=$(find "$dir" -maxdepth 1 -type f | wc -l | tr -d ' ')
  card_n=$(rg_count '^kind:\s*Card\s*$' "$dir")
  pill_n=$(rg_count '^kind:\s*Pill\s*$' "$dir")
  md_n=$(find "$dir" -maxdepth 1 -name '*.md' -type f | wc -l | tr -d ' ')
  asc_n=$(find "$dir" -maxdepth 1 -name '*.asc' -type f | wc -l | tr -d ' ')
  needs_dif_n=$(rg_count 'needs_dif:\s*true' "$dir")

  echo "=== cards_scan $dir ==="
  echo "total_files=$total"
  echo "kind_Card=$card_n"
  echo "kind_Pill=$pill_n"
  echo "markdown_docs=$md_n"
  echo "detached_signatures=$asc_n"
  echo "needs_dif_true=$needs_dif_n"

  other_yaml_n=$((total - card_n - pill_n - md_n - asc_n))
  if [ "$other_yaml_n" -gt 0 ]; then
    echo "unclassified=$other_yaml_n  (yaml files with neither 'kind: Card' nor 'kind: Pill' -- check by hand, or run tooling/bin/scan-hee-cards.py for full classification)"
  fi

  return 0
}
