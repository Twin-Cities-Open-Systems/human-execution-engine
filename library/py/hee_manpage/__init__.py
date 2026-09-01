"""Turn a tool's --help output into a REAL man page, not a transcript.

Operator, 2026-08-31: "what is on man.tcos now has randing '{}' and shit.
all pro style man for all our shit."

What was wrong with the old output. The generator wrapped raw --help in a
fenced code block and handed it to pandoc, which produced:

    .TH "" "" "" "" ""        empty title -- renders as "()" in the header
    .SH hee-attach(1)         the tool NAME used as a section heading

so every generated page showed "()" where a man page shows
"HEE-ATTACH(1)  HEE Tools  HEE-ATTACH(1)", and had no NAME, SYNOPSIS or
DESCRIPTION at all. The hand-authored pages look right precisely because
they set .TH and use real sections.

This module emits pandoc markdown with a title block and real headings, so
pandoc's man writer produces .TH and .SH NAME/.SH SYNOPSIS/... properly.

MUST be converted with `pandoc -f markdown-smart`. With smart typography on,
pandoc rewrites `--target` to an en-dash `-target`, which makes every option
in every page impossible to copy. That corruption does not exist today only
because the old fenced block protected it -- moving to structured markdown
reintroduces it unless smart is off.
"""

from __future__ import annotations

import re

SECTION_ORDER = ["NAME", "SYNOPSIS", "DESCRIPTION", "OPTIONS", "SUBCOMMANDS",
                 "ENVIRONMENT", "FILES", "EXIT STATUS", "EXAMPLES", "SEE ALSO"]

# A heading in a tool's own help: an ALL-CAPS line, alone, no trailing colon
# needed. Many hee tools already write help this way (hee-ver, hee-check), so
# their structure maps straight onto man sections instead of being flattened.
HEADING = re.compile(r"^(?P<h>[A-Z][A-Z /]{2,24})\s*:?\s*$")

# "hee-attach -- does the thing" / "hee-attach - does the thing"
TAGLINE = re.compile(r"^\s*(?P<name>[\w.-]+)\s+(?:--|—|-)\s+(?P<desc>\S.*)$")

USAGE_LABEL = re.compile(r"^\s*(usage|synopsis)\s*:?\s*$", re.I)
USAGE_INLINE = re.compile(r"^\s*(usage|synopsis)\s*:\s*(?P<rest>\S.*)$", re.I)


def _dedent(lines: list[str]) -> list[str]:
    body = [ln for ln in lines if ln.strip()]
    if not body:
        return []
    pad = min(len(ln) - len(ln.lstrip()) for ln in body)
    return [ln[pad:] if len(ln) >= pad else ln for ln in lines]


def parse(name: str, help_text: str) -> dict:
    """Split raw --help into man sections. Never invents content."""
    lines = help_text.replace("\t", "    ").splitlines()
    sections: dict[str, list[str]] = {}
    tagline = ""

    # A tagline anywhere in the first few lines gives us NAME.
    for ln in lines[:4]:
        m = TAGLINE.match(ln)
        if m and m.group("name").lower().lstrip("./").endswith(name.lower().lstrip("./")):
            tagline = m.group("desc").strip()
            break
    if not tagline:
        for ln in lines[:4]:
            m = TAGLINE.match(ln)
            if m:
                tagline = m.group("desc").strip()
                break

    # argparse shape, which is most of this repo's Python tools:
    #
    #     usage: hee-fields [-h] ...
    #            (continuation lines, indented)
    #
    #     <the description>
    #
    # The description is the first paragraph AFTER the usage block, so the
    # usage block has to be consumed first -- its continuation lines are
    # indented and would otherwise be mistaken for the description.
    if not tagline and lines and re.match(r"^\s*usage\s*:", lines[0], re.I):
        i = 1
        while i < len(lines) and (lines[i].startswith((" ", "\t")) and lines[i].strip()):
            i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i < len(lines):
            t = lines[i].strip()
            if t and not HEADING.match(lines[i]) and not t.endswith(":"):
                m = TAGLINE.match(t)
                t = m.group("desc").strip() if m else t
                tagline = re.split(r"(?<=[a-z0-9)])\.\s", t)[0].rstrip(".")

    # Some tools print the bare tool name, a blank, then the description --
    # hee-attach does exactly this. Without handling it, NAME degrades to the
    # useless "hee-attach - hee-attach command".
    if not tagline:
        for i, ln in enumerate(lines[:3]):
            if ln.strip().lstrip("./") == name.lstrip("./"):
                for nxt in lines[i + 1:i + 4]:
                    t = nxt.strip()
                    if t and not USAGE_LABEL.match(nxt) and not HEADING.match(nxt):
                        # First sentence only -- NAME is a one-liner by convention.
                        tagline = re.split(r"(?<=[a-z0-9)])\.\s", t)[0].rstrip(".")
                        break
                break

    current = "DESCRIPTION"
    buf: list[str] = []
    for ln in lines:
        m = HEADING.match(ln)
        inline = USAGE_INLINE.match(ln)
        if m:
            sections.setdefault(current, []).extend(buf)
            buf = []
            current = m.group("h").strip().upper()
            continue
        if USAGE_LABEL.match(ln):
            sections.setdefault(current, []).extend(buf)
            buf = []
            current = "SYNOPSIS"
            continue
        if inline and current == "DESCRIPTION" and "SYNOPSIS" not in sections:
            sections.setdefault(current, []).extend(buf)
            buf = []
            sections["SYNOPSIS"] = [inline.group("rest")]
            current = "DESCRIPTION"
            continue
        buf.append(ln)
    sections.setdefault(current, []).extend(buf)

    # Drop a leading tagline from DESCRIPTION -- it belongs to NAME.
    desc = sections.get("DESCRIPTION", [])
    while desc and not desc[0].strip():
        desc.pop(0)
    if desc and tagline and tagline in desc[0]:
        desc.pop(0)
    sections["DESCRIPTION"] = desc

    return {"tagline": tagline, "sections":
            {k: _dedent(v) for k, v in sections.items() if any(x.strip() for x in v)}}


def render(name: str, help_text: str, section: int = 1,
           manual: str = "HEE Tools") -> str:
    """Emit pandoc markdown that becomes a real man page."""
    parsed = parse(name, help_text)
    tagline = parsed["tagline"] or f"{name} command"
    secs = parsed["sections"]

    out = [f"% {name.upper()}({section}) | {manual}", "", "# NAME", "",
           f"{name} - {tagline}", ""]

    def emit(title: str, body: list[str]) -> None:
        if not body:
            return
        out.append(f"# {title}")
        out.append("")
        # Indented literal block: preserves the tool's own alignment, and
        # keeps pandoc from reinterpreting option dashes or brackets as
        # markdown syntax.
        for ln in body:
            out.append(f"    {ln}" if ln.strip() else "")
        out.append("")

    for title in SECTION_ORDER:
        if title in ("NAME",):
            continue
        if title in secs:
            emit(title, secs.pop(title))
    for title, body in secs.items():
        emit(title, body)

    return "\n".join(out).rstrip() + "\n"
