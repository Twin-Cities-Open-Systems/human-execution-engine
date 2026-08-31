"""hee_refs -- verify that file references in docs point at files that exist.

Why
---
Operator, 2026-08-31, after `hee print` failed on a path copied straight out
of a contract:

    hee print contracts/hee.kind-registry.contract.v1.yaml
    missing file: contracts/hee.kind-registry.contract.v1.yaml

The real path is `hee/contracts/hee.kind-registry.contract.v1.yaml`. The
reference in `contracts/agent-instance-signature-v1.contract.yaml` had lost
its `hee/` prefix, and nothing caught it. A first sweep found **141 broken
references across 100 distinct paths** in live docs -- roughly 15% of every
file reference in the repo pointing at nothing.

Existing CI did not catch this: `.github/workflows/docs.yaml` validates only
`[text](link)` markdown links inside `.md` files. It never looks at
backticked paths, and never looks at YAML or JSON at all -- which is exactly
where doctrine, contracts and blueprints reference each other.

Scope decisions
---------------
- `docs/history/**` is EXCLUDED. Those are point-in-time snapshots; a
  reference to a file that has since been deleted is correct history, not
  rot. Enforcing there would mean falsifying the record to satisfy a linter.
- Generated indexes (`hee/evidence/**`) are excluded for the same reason:
  they record what was on disk at generation time.
- A token only counts as a reference if its first path segment is a real
  top-level directory of the repo. That keeps `foo/bar` in prose, module
  paths, and URLs out of the results.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass

__all__ = ["Broken", "scan", "DOC_EXT", "EXCLUDE_PREFIXES"]

DOC_EXT = (".md", ".yaml", ".yml", ".json")
REF_EXT = (".md", ".yaml", ".yml", ".json", ".sh", ".py", ".bash",
           ".txt", ".mk", ".1", ".html", ".css", ".js")

EXCLUDE_PREFIXES = ("docs/history/", "hee/evidence/")

# A path-ish token inside backticks, quotes, parens or whitespace.
_REF = re.compile(r"""[`"'(\s]([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.@-]+)+)[`"')\s,;:]""")


@dataclass(frozen=True)
class Broken:
    ref: str          # the reference as written
    source: str       # the doc containing it
    line: int         # 1-based line number
    suggestion: str   # a real path with the same basename, or ""


def _tracked(root: str) -> list[str]:
    out = subprocess.run(["git", "-C", root, "ls-files"],
                         capture_output=True, text=True)
    return out.stdout.split() if out.returncode == 0 else []


def scan(root: str = ".", include_history: bool = False) -> tuple[int, list[Broken]]:
    """Return (references_checked, broken). Deterministic, ordered by source."""
    files = _tracked(root)
    if not files:
        return 0, []

    tops = {d for d in os.listdir(root)
            if os.path.isdir(os.path.join(root, d)) and not d.startswith(".")}

    # basename -> real paths, for suggesting the correct location
    by_base: dict[str, list[str]] = {}
    for f in files:
        by_base.setdefault(os.path.basename(f), []).append(f)

    existing = set(files)
    checked = 0
    broken: list[Broken] = []

    for f in sorted(files):
        if not f.endswith(DOC_EXT):
            continue
        if not include_history and f.startswith(EXCLUDE_PREFIXES):
            continue
        try:
            text = open(os.path.join(root, f), errors="ignore").read()
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in _REF.finditer(" " + line + " "):
                ref = m.group(1)
                head = ref.split("/", 1)[0]
                if head not in tops:
                    continue
                tail = ref.rsplit("/", 1)[-1]
                if not ref.endswith(REF_EXT) and "." not in tail:
                    continue
                checked += 1
                if ref in existing or os.path.exists(os.path.join(root, ref)):
                    continue
                cands = by_base.get(os.path.basename(ref), [])
                broken.append(Broken(ref, f, lineno,
                                     cands[0] if len(cands) == 1 else ""))
    return checked, broken


def repair(root: str = ".", broken: list[Broken] | None = None) -> list[tuple[str, str, str]]:
    """Repair references that have exactly one real candidate.

    Returns [(source, old_ref, new_ref), ...] actually changed.

    THE BUG THIS EXISTS TO NOT REPEAT (2026-08-31): the first version looped
    once per broken *occurrence* and called ``str.replace``, which replaces
    ALL occurrences. So the second occurrence of the same ref re-ran the
    replacement against text that was already corrected, matching the short
    ref *inside* the newly-written long one and producing `hee/hee/contracts/`.
    It corrupted 16 tracked files before being reverted.

    Two defences, both required:
      1. de-duplicate by (source, ref) so each ref is replaced once per file
      2. anchor the match so a ref is never matched when it is already
         preceded by a path segment -- i.e. never rewrite the tail of an
         already-correct path.
    """
    if broken is None:
        _, broken = scan(root)

    per_file: dict[str, dict[str, str]] = {}
    for b in broken:
        if not b.suggestion or b.suggestion == b.ref:
            continue
        per_file.setdefault(b.source, {}).setdefault(b.ref, b.suggestion)

    changed: list[tuple[str, str, str]] = []
    for src, mapping in per_file.items():
        path = os.path.join(root, src)
        try:
            text = original = open(path, errors="ignore").read()
        except OSError:
            continue
        # longest refs first, so a short ref cannot pre-empt a longer one
        for ref in sorted(mapping, key=len, reverse=True):
            new = mapping[ref]
            # not preceded by a path char: never match inside a longer path
            pat = re.compile(r"(?<![A-Za-z0-9_./-])" + re.escape(ref) + r"(?![A-Za-z0-9_])")
            text, n = pat.subn(new, text)
            if n:
                changed.append((src, ref, new))
        if text != original:
            # refuse to write anything that created a doubled path segment
            if re.search(r"\b(\w+)/\1/", text) and not re.search(r"\b(\w+)/\1/", original):
                raise RuntimeError(f"repair would corrupt {src}: doubled path segment")
            open(path, "w").write(text)
    return changed


def discover_repos(path: str) -> list[str]:
    """Return every git repo to check under `path`.

    - `path` is itself a git repo  -> [that repo]
    - `path` is a directory of repos (e.g. ~/git) -> each child repo
    - neither -> []

    Deliberately only one level deep. Recursing arbitrarily would descend
    into vendored checkouts, worktrees and node_modules, and turn a quick
    check into a filesystem crawl.
    """
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isdir(path):
        return []
    if os.path.exists(os.path.join(path, ".git")):
        return [path]
    out = []
    for name in sorted(os.listdir(path)):
        child = os.path.join(path, name)
        if os.path.isdir(child) and os.path.exists(os.path.join(child, ".git")):
            out.append(child)
    return out


def repo_root(start: str = ".") -> str:
    """The git top-level containing `start`, or `start` itself if not in a repo."""
    r = subprocess.run(["git", "-C", start, "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else os.path.abspath(start)
