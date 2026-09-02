"""hee_locale -- does a repo's authored text match the locale it declares.

Not a list of mistakes. Operator, 2026-09-01:

    "make the tool more of a locale verification tool, not a 'we hate the
    brits' tool"

Neither English locale is wrong. A repo DECLARES one, and this reports the
words that do not match it. Declare ``en_GB`` and ``color`` is what gets
flagged; the machinery is the same in both directions.

TCOS declares ``en_US`` because its operator is in the US and its public
content is US-facing. That is a fact about TCOS, not about English.

Three inputs
------------
1. ``library/locale/en.yaml`` -- 36 variant pairs. Data, not policy: which
   column is correct depends entirely on the declared locale.

2. ``HEE_LOCALE`` -- what this repo writes. Default ``en_US``. Set it in
   heerc, per the org's rc-file preference, not in a script.

3. The primitives repo's ``external.yaml`` -- which external tools spell
   their own CONFIGURATION VOCABULARY in another locale, and in which files.

Why the third input exists
--------------------------
A tool's option names are its API, not prose. tmux spells its own options
``colour39``, ``display-panes-colour``, ``fg=colour232``. Rewriting those to
US spelling breaks the config, so a checker that does not know this tells an
operator to introduce a bug. It did: 17 findings in one .tmux.conf, all
false positives.

That fact is recorded where the tool's other provenance already lives --
primitives' registry answers "what version, verified how, from where", and
"what locale is its vocabulary" is the same kind of fact. Carrying a
hardcoded exception list here instead would put the fact in the one place
nothing else can discover it.

The registry is found via ``HEE_PRIMITIVES``, else ``$HOME/git/primitives``
(this org's own workspace convention, per bin/init-org.sh). When it is not
there, the check still runs and SAYS SO -- a silently-degraded exemption is
how a false positive comes back.

Position, not shape
-------------------
A word is only a locale finding when it stands alone as English: preceded by
whitespace, a quote or an open paren, and followed by whitespace, end of
line, or sentence punctuation that is itself followed by whitespace.

Anything else -- a sigil, an operator, a digit, an underscore, a dot, a
brace -- means it is a token, not prose. That rule was reached by inverting
a failed one: a blacklist of identifier SHAPES cleared tmux and still
flagged ``$colour``, ``--colour=always``, ``colour: red``, ``theme.colour.fg``
and ``colour_scheme``. A blacklist of shapes can never be finished.
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass

__all__ = ["Finding", "load_variants", "load_tool_locales", "build_pattern", "scan_line"]

DEFAULT_LOCALE = "en_US"

#: Marker exempting the line it appears on, matching `hee check refs`.
SUPPRESS = re.compile(r"hee-check:\s*(locale|style)-ok")

_LEAD = r"(^|[\s\"'(])"
_TAIL = r"($|\s|[.,;!?)\"'](\s|$))"


@dataclass
class Finding:
    """One word in the wrong locale, and what the declared locale spells it."""

    word: str
    expected: str
    locale: str


def _yaml():
    import yaml  # deferred: help must work without pyyaml installed
    return yaml


def load_variants(path: str) -> list[tuple[str, str]]:
    """The en_GB/en_US pairs, in registry order."""
    with open(path) as fh:
        doc = _yaml().safe_load(fh)
    pairs = [(a, b) for a, b in doc["spec"]["variants"]]

    # A pair whose sides are identical is not a variant -- it is a registry
    # that got edited by a careless sweep, and it makes the checker report
    # the CORRECT spelling as wrong. That happened: a `sed s/recognise/
    # recognize/g` meant for prose also rewrote the en_GB column of four
    # pairs, and the next run flagged `recognized` and asked for
    # `recognized`. Cheap to assert, and it fails loudly instead of lying.
    collapsed = [a for a, b in pairs if a == b]
    if collapsed:
        raise ValueError(
            "locale registry has identical pairs, so one side was overwritten: "
            + ", ".join(collapsed))
    return pairs


def load_tool_locales(registry: str | None) -> list[dict]:
    """External tools whose config vocabulary is another locale.

    Returns [] when the registry is absent -- the caller is expected to say
    so rather than pretend the exemption was applied.
    """
    if not registry or not os.path.exists(registry):
        return []
    with open(registry) as fh:
        doc = _yaml().safe_load(fh) or {}
    out = []
    for entry in (doc.get("spec", {}) or {}).get("entries", []) or []:
        loc = entry.get("locale")
        if loc and loc.get("config"):
            out.append({
                "name": entry.get("name"),
                "locale": loc["config"],
                "vocabulary": [w.lower() for w in loc.get("vocabulary", [])],
                "globs": loc.get("config_globs", []),
            })
    return out


def _cased(word: str) -> str:
    """`colour` -> `[Cc]olour`. Capitalization is derived, never listed."""
    return "[%s%s]%s" % (word[0].upper(), word[0], word[1:])


def build_pattern(variants: list[tuple[str, str]], locale: str) -> re.Pattern:
    """Words that do NOT match `locale`, in prose position only."""
    idx = 0 if locale == DEFAULT_LOCALE else 1
    words = "|".join(_cased(pair[idx]) for pair in variants)
    return re.compile(_LEAD + "(" + words + ")" + _TAIL)


def scan_line(line: str, path: str, rx: re.Pattern,
              variants: list[tuple[str, str]], locale: str,
              tool_locales: list[dict]) -> Finding | None:
    """One finding for a line, or None."""
    if SUPPRESS.search(line):
        return None
    m = rx.search(line)
    if not m:
        return None
    word = m.group(2)
    low = word.lower()

    # A tool that declares this vocabulary, in a file it declares it for.
    for tool in tool_locales:
        if low in tool["vocabulary"] and any(
                fnmatch.fnmatch(os.path.basename(path), g) or fnmatch.fnmatch(path, g)
                for g in tool["globs"]):
            return None

    idx = 0 if locale == DEFAULT_LOCALE else 1
    other = {a.lower(): b for a, b in variants} if idx == 0 else {b.lower(): a for a, b in variants}
    want = other.get(low, "")
    if word[0].isupper() and want:
        want = want[0].upper() + want[1:]
    return Finding(word=word, expected=want, locale=locale)
