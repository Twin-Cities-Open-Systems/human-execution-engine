"""hee_hostmap -- shared *.tcos.us hostname/path pattern matching.

Real trigger (2026-08-28): while defining the real lab.tcos.us <->
tcos.us sync policy, Spencer named the real target hostname shape --
"{<agent>|<oper>}.{blog,media,foo}[.lab]?.tcos.us" -- and asked for a
real regex to add to the library, "leave obvious room for expansion."
One real implementation, so SITEMAP.yaml validation, hee-view --sites,
and any future tool that needs to classify a *.tcos.us hostname share
the same pattern instead of N slightly-different copies.

Real shape, confirmed against every known-real hostname this session
(see the org's .github/profile/SITEMAP.yaml and SITEMAP-PROPOSED.yaml):
  <service>.tcos.us                    -- e.g. foo.tcos.us (shared slot)
  <person>.<service>.tcos.us           -- e.g. spencer.media.tcos.us
  <service>.lab.tcos.us                -- lab mirror, no person
  <person>.<service>.lab.tcos.us       -- lab mirror, per-person
  tcos.us / lab.tcos.us                -- bare apex, either env

<person> covers both an Oper name (spencer) and an Agent name
(touchy-claude) -- this module can't and doesn't try to tell which:
that classification lives in SITEMAP metadata, not the DNS label
itself. SERVICES is deliberately a plain set, not baked into the
regex by hand, so adding a new service is a one-line change here, not
a regex rewrite.

Real, deliberate exclusions -- not a gap: rtfm.tcos.us/man.tcos.us
(external DigitalOcean infra, outside this pattern entirely) and dead
names like www.tcos.us/resume.tcos.us correctly fail to match. A
non-match doesn't mean "invalid" on its own -- callers decide what an
unmatched host means (external infra, typo, needs a new SERVICES
entry); this module only classifies, it doesn't judge.
"""
import re

SERVICES = {"blog", "media", "foo"}

_LABEL = r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"


def _build_hostname_re(services):
    service_alt = "|".join(sorted(services))
    return re.compile(
        rf"^(?:(?P<person>{_LABEL})\.)?"
        rf"(?P<service>{service_alt})"
        rf"(?:\.(?P<env>lab))?"
        rf"\.tcos\.us$"
    )


HOSTNAME_RE = _build_hostname_re(SERVICES)
APEX_RE = re.compile(r"^(?:(?P<env>lab)\.)?tcos\.us$")

# Clean slug paths only -- no extension, no trailing slash, no
# "/index.html" ugliness. '/' (root) and '/a/b/c' are valid; anything
# with a dot or an empty path segment is not.
PATH_SLUG_RE = re.compile(rf"^/(?:{_LABEL}(?:/{_LABEL})*)?$")


def classify_host(host):
    """Classify a real hostname against the org's real
    {person}.{service}[.lab].tcos.us pattern or the bare/lab apex.

    Returns a dict (apex: person=service=None; service host: person
    may be None) with keys person/service/env, or None if HOST
    matches neither shape. Case-insensitive; HOST should not include
    a scheme or path.
    """
    host = host.lower()
    m = APEX_RE.match(host)
    if m:
        return {"person": None, "service": None, "env": m.group("env")}
    m = HOSTNAME_RE.match(host)
    if m:
        return {
            "person": m.group("person"),
            "service": m.group("service"),
            "env": m.group("env"),
        }
    return None


def is_clean_path(path):
    """True if PATH is a real clean slug path -- '/', '/contracts',
    '/people/spencer' -- not '/contracts.html', '/index.html', or a
    trailing/double slash."""
    return bool(PATH_SLUG_RE.match(path))
