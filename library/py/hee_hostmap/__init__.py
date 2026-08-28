"""hee_hostmap -- shared *.tcos.us hostname/path pattern matching.

Real trigger (2026-08-28): while defining the real lab.tcos.us <->
tcos.us sync policy, Spencer named the real target hostname shape --
"{<agent>|<oper>}.{blog,media,foo}[.lab]?.tcos.us" -- and asked for a
real regex to add to the library, "leave obvious room for expansion."
One real implementation, so SITEMAP.yaml validation, hee-view --sites,
and any future tool that needs to classify a *.tcos.us hostname share
the same pattern instead of N slightly-different copies.

Real shape:
  <service>.tcos.us                    -- e.g. foo.tcos.us (shared slot)
  <person>.<service>.tcos.us           -- e.g. spencer.media.tcos.us
  <service>.lab.tcos.us                -- lab mirror, no person
  <person>.<service>.lab.tcos.us       -- lab mirror, per-person
  tcos.us / lab.tcos.us                -- bare apex, either env

<person> covers both an Oper name (spencer) and an Agent name
(touchy-claude) -- this module can't and doesn't try to tell which:
that classification lives in SITEMAP metadata, not the DNS label
itself.

Real correction #1, same session, Spencer direct: an earlier version
restricted <service> to a hardcoded alternation (blog|media|foo|man)
-- "the process to add a new service will include updating a regex?
that sound like a poor regex... make a regex that will work for
anything we may want to add, that is the whole point." <service> now
matches generically, the same DNS-label shape as <person> -- adding a
real service (or a per-person sandbox under one) needs zero code
changes. Known/intentional service names live only in
test_hee_hostmap.py, as real example data proving the pattern still
classifies them correctly -- not as a matching constraint.

Real correction #2, same session, caught by this module's own test
suite: a single combined regex for "(person.)?service(.lab)?.tcos.us"
is genuinely ambiguous once <service> is unrestricted -- for
"ns1.lab.tcos.us", Python's re greedily matches person=ns1,
service=lab, env=None (a real, fully-matching parse) and never
backtracks to try person=None, service=ns1, env=lab, because it
already found *a* match. classify_host() below resolves this by
splitting on the ".lab.tcos.us" / ".tcos.us" suffix FIRST
(deterministic, no ambiguity), then parsing whatever's left as
(person.)?service -- not by tuning one regex to get luckier.

This module answers "does this hostname have the right shape," not
"is this a real, provisioned host" -- that's SITEMAP.yaml's job
(existence), not this module's (shape). A non-match here means the
apex/service form doesn't apply at all (wrong TLD, extra labels,
malformed) -- everything else, real or not, matches structurally and
judging realness happens elsewhere.
"""
import re

_LABEL = r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"

# Unambiguous on their own -- no <service>-vs-env overlap to resolve.
APEX_RE = re.compile(r"^(?:lab\.)?tcos\.us$")
_PREFIX_RE = re.compile(rf"^(?:(?P<person>{_LABEL})\.)?(?P<service>{_LABEL})$")

# Clean slug paths only -- no extension, no trailing slash, no
# "/index.html" ugliness. '/' (root) and '/a/b/c' are valid; anything
# with a dot or an empty path segment is not.
PATH_SLUG_RE = re.compile(rf"^/(?:{_LABEL}(?:/{_LABEL})*)?$")

_SUFFIXES = (("lab", ".lab.tcos.us"), (None, ".tcos.us"))


def classify_host(host):
    """Classify a real hostname against the org's real
    {person}.{service}[.lab].tcos.us pattern or the bare/lab apex.

    Returns a dict (apex: person=service=None; service host: person
    may be None) with keys person/service/env, or None if HOST
    matches neither shape. Case-insensitive; HOST should not include
    a scheme or path. Matching is shape-only -- a real dict result
    doesn't mean the host is actually live; check SITEMAP.yaml for
    that.
    """
    host = host.lower()
    if APEX_RE.match(host):
        return {"person": None, "service": None, "env": "lab" if host.startswith("lab.") else None}
    for env, suffix in _SUFFIXES:
        if host.endswith(suffix):
            prefix = host[: -len(suffix)]
            m = _PREFIX_RE.match(prefix)
            if m:
                return {
                    "person": m.group("person"),
                    "service": m.group("service"),
                    "env": env,
                }
            return None
    return None


def is_clean_path(path):
    """True if PATH is a real clean slug path -- '/', '/contracts',
    '/people/spencer' -- not '/contracts.html', '/index.html', or a
    trailing/double slash."""
    return bool(PATH_SLUG_RE.match(path))
