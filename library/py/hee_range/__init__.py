"""hee_range -- shared id/range/regex selection logic.

Real trigger (2026-08-24): hee-ticket's -close and hee-git-merge's
-r/--regex had each grown their own item-selection logic independently.
Spencer's direct ask: "make sure all that have a range use this same
range" -- "should we add the regex range function go in as a sub sub
module so it can be maintained sep... don't want to update all sub tools
when a regex change is req." One real implementation, imported by every
tool that needs to pick a subset of items by id/range/pattern, instead
of N slightly-different copies.

Not the same concept as a time-duration window (see hee-publish's
-range "<N> <unit>", min/hrs/day/wks/sess) -- that resolves to a
timestamp, this resolves to a subset of items. Different problem,
deliberately not merged into this module.
"""
import re

_ID_RANGE_RE = re.compile(r"[\d,\-\s]+")


def is_id_range_spec(spec: str) -> bool:
    """True if SPEC looks like a bare id/range list (1,2,3 / 1-3 /
    1-3,7,9) rather than a regex. A real regex almost never fullmatches
    this shape, so one check safely distinguishes the two forms."""
    return bool(_ID_RANGE_RE.fullmatch(spec))


def parse_id_range(spec: str) -> set:
    """Expand an id/range SPEC (already confirmed via is_id_range_spec)
    into the set of requested id strings, e.g. '1-3,7' -> {'1','2','3','7'}.
    Not zero-padded -- callers normalize to their own id format."""
    wanted = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            wanted.update(str(n) for n in range(int(lo), int(hi) + 1))
        else:
            wanted.add(part)
    return wanted


def resolve_spec(spec, items, get_id, get_haystack):
    """Resolve SPEC against ITEMS (a list of arbitrary objects).

    SPEC is either a digits/commas/hyphens id+range list (1,2,3 / 1-3 /
    1-3,7,9) matched against get_id(item), zero-padding-insensitive -- or,
    if it contains anything else, a case-insensitive regex matched
    against get_haystack(item).

    get_id(item) -> str, get_haystack(item) -> str (may return None,
    treated as "").

    Returns the matching subset of ITEMS, in ITEMS' original order.
    """
    if is_id_range_spec(spec):
        wanted_norm = {w.lstrip("0") or "0" for w in parse_id_range(spec)}
        return [it for it in items if (get_id(it).lstrip("0") or "0") in wanted_norm]

    pattern = re.compile(spec, re.IGNORECASE)
    return [it for it in items if pattern.search(get_haystack(it) or "")]
