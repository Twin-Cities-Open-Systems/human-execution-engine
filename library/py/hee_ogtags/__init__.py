"""hee_ogtags -- shared Open Graph / Twitter Card / title / canonical
tag extraction from raw HTML.

Real trigger (2026-08-29): Spencer manually ran a curl+grep one-liner
twice in the same session to eyeball OG tags on live TCOS pages
(spencer.blog.tcos.us/resume-spencer, spencer.media.tcos.us/tux-tattoo/),
then asked to "roll this into a hee tool" -- the real, working regex
from that one-liner is promoted here as the shared implementation,
consumed by tooling/bin/hee-check-og, instead of staying a copy-pasted
shell command nobody else can reuse.

No generic "regex library" exists anywhere in this org (checked
2026-08-29 -- only Rust's own regex crate build artifacts in
MT-logo-render, unrelated) -- library/py/'s own real precedent
(hee_hostmap, hee_range) is one focused module per real concern, not a
grab-bag. This module follows that shape rather than starting a
"catch-all regex" module that would immediately fight the established
convention.

Deliberately regex-based, not a real HTML parser (BeautifulSoup/lxml)
-- matches the org's other markup-scanning tools
(.github/bin/check_render_review_compliance.py), good enough for
well-formed, single-line meta tags, which is what every real OG tag in
this org's own Gold-based pages actually is. Static HTML only: this
sees what the server actually sends, not anything injected by
client-side JS after load.
"""
import re

# A <meta ...> tag, allowing a ">" inside a quoted attribute value (a
# description that says "<person>.blog.tcos.us" ended the old match early
# and the tag vanished, 2026-09-06). Attributes are read as a set, in any
# order, so an id= between property= and content= no longer hides a tag.
_META_TAG_RE = re.compile(r'<meta\b(?:[^>"]|"[^"]*")*>', re.I)
_ANY_ATTR_RE = re.compile(r'([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*"([^"]*)"')
OG_META_RE = re.compile(r'<meta\b(?:[^>"]|"[^"]*")*property="og:[^"]*"(?:[^>"]|"[^"]*")*>', re.I)
TWITTER_META_RE = re.compile(r'<meta\b(?:[^>"]|"[^"]*")*name="twitter:[^"]*"(?:[^>"]|"[^"]*")*>', re.I)
TITLE_RE = re.compile(r'<title>[^<]*</title>')
CANONICAL_RE = re.compile(r'<link rel="canonical"[^>]*>')
# every tag, in document order (--raw)
ALL_TAGS_RE = re.compile("|".join(p.pattern for p in (OG_META_RE, TWITTER_META_RE, TITLE_RE, CANONICAL_RE)), re.I)


def extract_tags(html):
    """Return every real OG/Twitter/title/canonical tag found in HTML,
    in document order, exactly as they appear (raw tag text) -- same
    shape `curl | grep -oE` produces, not a parsed/deduplicated dict.
    """
    return ALL_TAGS_RE.findall(html)


def extract_meta_pairs(html: str) -> dict:
    """{property-or-name: content} for every og:* and twitter:* meta tag,
    first occurrence wins, attribute order and extra attributes ignored."""
    pairs = {}
    for tag in _META_TAG_RE.findall(html):
        attrs = {k.lower(): v for k, v in _ANY_ATTR_RE.findall(tag)}
        key = attrs.get("property") or attrs.get("name")
        if not key or not (key.startswith("og:") or key.startswith("twitter:")):
            continue
        if key not in pairs:
            pairs[key] = attrs.get("content", "")
    return pairs
