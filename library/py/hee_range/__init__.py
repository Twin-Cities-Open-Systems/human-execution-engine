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


def parse_id_range_ordered(spec: str) -> list:
    """Expand an id/range SPEC into the requested ids IN THE ORDER WRITTEN,
    e.g. '475,470,473' -> ['475', '470', '473'].

    Operator, 2026-08-31: "we have a range selector for prs, it should be a
    set (order mandated from entry as arg)". The order is the point: merging
    is order-sensitive, and `-r '475,470,473'` means 475 has to land first
    because the others depend on it. Sorting that back into 470,473,475
    silently does the opposite of what was asked.

    A hyphen range expands ascending in place, since '10-12' has no other
    sensible reading. Duplicates collapse to their FIRST mention, so
    '3,1,3' is ['3','1'] -- an id cannot be in two places at once.
    """
    out = []
    seen = set()

    def add(v):
        if v not in seen:
            seen.add(v)
            out.append(v)

    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            for n in range(int(lo), int(hi) + 1):
                add(str(n))
        else:
            add(part)
    return out


def parse_id_range(spec: str) -> set:
    """Set form, kept for callers that genuinely do not care about order."""
    return set(parse_id_range_ordered(spec))


def resolve_spec(spec, items, get_id, get_haystack):
    """Resolve SPEC against ITEMS (a list of arbitrary objects).

    SPEC is either a digits/commas/hyphens id+range list (1,2,3 / 1-3 /
    1-3,7,9) matched against get_id(item), zero-padding-insensitive -- or,
    if it contains anything else, a case-insensitive regex matched
    against get_haystack(item).

    get_id(item) -> str, get_haystack(item) -> str (may return None,
    treated as "").

    An id/range SPEC returns matches in SPEC order (it is an ordered set).
    A regex SPEC returns them in ITEMS order, since a pattern expresses no
    ordering of its own.
    """
    if is_id_range_spec(spec):
        # Returned in SPEC order, not ITEMS order -- an explicit id list is an
        # ordered set, and the caller wrote that order deliberately.
        wanted = [w.lstrip("0") or "0" for w in parse_id_range_ordered(spec)]
        rank = {w: i for i, w in enumerate(wanted)}
        matched = [it for it in items if (get_id(it).lstrip("0") or "0") in rank]
        return sorted(matched, key=lambda it: rank[get_id(it).lstrip("0") or "0"])

    pattern = re.compile(spec, re.IGNORECASE)
    return [it for it in items if pattern.search(get_haystack(it) or "")]
