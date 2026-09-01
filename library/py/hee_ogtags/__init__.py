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

OG_META_RE = re.compile(r'<meta[^>]*property="og:[^"]*"[^>]*>')
TWITTER_META_RE = re.compile(r'<meta[^>]*name="twitter:[^"]*"[^>]*>')
TITLE_RE = re.compile(r'<title>[^<]*</title>')
CANONICAL_RE = re.compile(r'<link rel="canonical"[^>]*>')

# Real, live-tested full sweep -- same four alternatives Spencer ran by
# hand: OG tags, Twitter Card tags, <title>, and the canonical link.
# These are the things that actually matter for a link preview.
ALL_TAGS_RE = re.compile(
    "|".join(p.pattern for p in (OG_META_RE, TWITTER_META_RE, TITLE_RE, CANONICAL_RE))
)

_ATTR_RE = re.compile(r'(property|name)="([^"]+)"\s+content="([^"]*)"')
_ATTR_RE_REVERSED = re.compile(r'content="([^"]*)"\s+(?:property|name)="([^"]+)"')


def extract_tags(html):
    """Return every real OG/Twitter/title/canonical tag found in HTML,
    in document order, exactly as they appear (raw tag text) -- same
    shape `curl | grep -oE` produces, not a parsed/deduplicated dict.
    """
    return ALL_TAGS_RE.findall(html)


def extract_meta_pairs(html):
    """Return a dict of {property_or_name: content} for every real
    og:*/twitter:* meta tag found (property="..." content="..." or
    content="..." property="..." attribute order, both real -- some
    pages emit one order, some the other). Later duplicate keys
    overwrite earlier ones, same as a browser's own last-wins DOM
    behavior for repeated meta tags.
    """
    pairs = {}
    for tag in OG_META_RE.findall(html) + TWITTER_META_RE.findall(html):
        m = _ATTR_RE.search(tag) or _ATTR_RE_REVERSED.search(tag)
        if m:
            groups = m.groups()
            if len(groups) == 3:
                _, key, value = groups
            else:
                value, key = groups
            pairs[key] = value
    return pairs
