"""hee_gtag -- the org's Google tag (GA4) snippet, one source for every
page generator that publishes live.

Real trigger (2026-09-05, Spencer): "make sure we have this tag on
everything we publish live." Five generators emit pages for tcos.us
hosts (tcos-www's generate-public-site.py, resume's convert.sh hubs,
render-blog.py via .github's render-review.py, the media-item builder,
and the media root/tux-tattoo pages). A snippet pasted five times is the
drift the org already paid for with tc-theme.js. One function instead.

The measurement ID is NOT here: it is org identity and lives on the
branding card (tcos-audit policy/branding.card.v1.yaml,
spec.analytics.ga4_measurement_id), read via $HEE_BRANDING like every
other org-specific value. HEE stays org-agnostic.

Reporting is guarded to production hostnames -- any *.tcos.us that is
not *.lab.tcos.us -- so lab mirrors, localhost and file:// load the
library but never send a hit. Deterministic; no GA-side filter to keep
in sync.

Same shape as the sibling modules (hee_ogtags, hee_hostmap): one focused
concern, consumed by tools, no CLI of its own.
"""
import os
import re

# (^|\\.) on both: the apex "tcos.us" has no leading dot, so /\\.tcos\\.us$/
# never matched it and the home site never reported (measured 2026-09-06,
# GA empty after the tag shipped); and "lab.tcos.us" itself must be excluded,
# not only *.lab.tcos.us.
PROD_GUARD_JS = "/(^|\\.)tcos\\.us$/.test(location.hostname) && !/(^|\\.)lab\\.tcos\\.us$/.test(location.hostname)"
_ID_RE = re.compile(r"^G-[A-Z0-9]{6,12}$")
# Where the org's branding card lives on an operator machine (every repo is
# checked out under ~/git, the org's own convention). Used when
# $HEE_BRANDING is unset, so a build on kiosk cannot silently lose the tag.
DEFAULT_BRANDING = os.path.expanduser("~/git/tcos-audit/policy/branding.card.v1.yaml")


def measurement_id(branding_path=None):
    """The GA4 measurement ID from the branding card. None when there is no
    card or the card has no analytics block -- callers decide whether that
    is a warning (skip the tag) or an error."""
    path = branding_path or os.environ.get("HEE_BRANDING") or DEFAULT_BRANDING
    if not path or not os.path.isfile(path):
        return None
    try:
        import yaml
        spec = yaml.safe_load(open(path))["spec"]
        mid = spec.get("analytics", {}).get("ga4_measurement_id")
    except Exception:
        return None
    return mid if mid and _ID_RE.match(mid) else None


def snippet(mid, indent=""):
    """The gtag.js block, to be placed immediately after <head> -- Google's
    own instruction and where its detector looks. Plain single braces:
    a caller that later runs str.format() on the page must double them
    itself (tcos-www's generator already does that for THEME_HEAD)."""
    if not mid or not _ID_RE.match(mid):
        raise ValueError(f"hee_gtag: not a GA4 measurement ID: {mid!r}")
    lines = [
        "<!-- Google tag (gtag.js) -->",
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={mid}"></script>',
        "<script>",
        "  window.dataLayer = window.dataLayer || [];",
        "  function gtag(){dataLayer.push(arguments);}",
        "  gtag('js', new Date());",
        "  // production only: *.lab.tcos.us, localhost and file:// load this but never report",
        f"  if ({PROD_GUARD_JS}) {{",
        f"    gtag('config', '{mid}');",
        "  }",
        "</script>",
    ]
    return "\n".join(indent + l for l in lines)


def snippet_or_empty(branding_path=None, indent="", warn=True):
    """The snippet for the card's ID. Without an ID this is CRITICAL and
    exits -- a page built without the tag is a page that will be deployed
    without the tag. Real trigger, 2026-09-06: tcos-www's pages were
    regenerated with $HEE_BRANDING unset, this printed a WARNING and
    returned "", the tagless pages were committed and deployed, and GA
    reported "tag not detected" on tcos.us. The two places a tagless page
    is legitimate say so explicitly: CI (no private tcos-audit checkout,
    the page is never deployed from there) and HEE_GTAG_OPTIONAL=1."""
    mid = measurement_id(branding_path)
    if not mid:
        import sys
        if os.environ.get("CI") or os.environ.get("HEE_GTAG_OPTIONAL") == "1":
            if warn:
                print("⚠️  WARNING hee_gtag: no ga4_measurement_id (branding card not found) -- page built without the Google tag; allowed here (CI / HEE_GTAG_OPTIONAL=1)", file=sys.stderr)
            return ""
        sys.exit("❌ CRITICAL hee_gtag: no ga4_measurement_id -- set $HEE_BRANDING to the branding card "
                 f"(default {DEFAULT_BRANDING}). Refusing to build a page without the Google tag; "
                 "HEE_GTAG_OPTIONAL=1 if that is really intended.")
    return snippet(mid, indent)
