#!/usr/bin/env python3
"""Build a single, current, chronological index of docs/history/*_capsules
("pills"), so history_recap (blueprints/shift-init-v1.yaml) has one always
-current document to read instead of walking dozens of raw files by hand.

Per human-execution-engine#225: absorption by tool, not by manual re-dating
of the old files. Read-only against the source pills -- this never rewrites
them, only regenerates the generated index.

Usage:
    python3 tools/hee-pill-index.py [--write]

Without --write, prints the index to stdout (dry run). With --write,
overwrites docs/history/PILL_INDEX.md.
"""
from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import sys

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required (pip install pyyaml)", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CAPSULE_DIRS = [
    REPO_ROOT / "docs" / "history" / "state_capsules",
    REPO_ROOT / "docs" / "history" / "status_capsules",
]
OUTPUT_PATH = REPO_ROOT / "docs" / "history" / "PILL_INDEX.md"
GENERATED_FILE_NAMES = {"PILL_INDEX.md", "README.md", "CURRENT_TASKS.md"}

DATE_IN_PATH_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
DATE_IN_NAME_RE = re.compile(r"(\d{4})(\d{2})(\d{2})T\d{6}Z")


class Pill:
    def __init__(self, path: pathlib.Path, date: str | None, title: str, summary: str):
        self.path = path
        self.date = date or "unknown-date"
        self.title = title
        self.summary = summary

    def sort_key(self):
        # unknown-date pills sort last, not first -- don't let missing
        # metadata masquerade as "oldest" or "newest"
        return (self.date == "unknown-date", self.date, str(self.path))


DATE_KEYS = ("date", "timestamp", "asof")


def guess_date(path: pathlib.Path, parsed: dict | None) -> str | None:
    """Best-effort date extraction. Never fabricates -- returns None if
    nothing real is found, caller sorts those last."""
    if parsed:
        for key in DATE_KEYS:
            v = parsed.get(key)
            if isinstance(v, (str, datetime.date, datetime.datetime)):
                return str(v)[:10]
        # one level of nesting -- covers context.timestamp, pill.date,
        # state.asof, and similar without hardcoding every schema seen
        for v in parsed.values():
            if isinstance(v, dict):
                for key in DATE_KEYS:
                    nested = v.get(key)
                    if isinstance(nested, (str, datetime.date, datetime.datetime)):
                        return str(nested)[:10]

    m = DATE_IN_NAME_RE.search(path.name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    m = DATE_IN_PATH_RE.search(str(path.relative_to(REPO_ROOT)))
    if m:
        return m.group(1)

    return None


def guess_title(path: pathlib.Path, parsed: dict | None, raw_text: str) -> str:
    if parsed:
        for key in ("chat", "name"):
            if isinstance(parsed.get(key), str):
                return parsed[key]
        pill = parsed.get("pill")
        if isinstance(pill, dict) and isinstance(pill.get("id"), str):
            return pill["id"]
        state = parsed.get("state")
        if isinstance(state, dict) and isinstance(state.get("name"), str):
            return state["name"]

    if path.suffix == ".md" or path.name.endswith(".md.done"):
        # "# " only means a markdown heading in .md files -- in .yaml
        # files it's a comment (e.g. this repo's "# path: ..." header
        # convention), not a title
        for line in raw_text.splitlines():
            line = line.strip()
            if line.startswith("# "):
                return line.lstrip("# ").strip()

    return path.stem


def guess_summary(parsed: dict | None, raw_text: str) -> str:
    if parsed:
        for key in ("purpose",):
            v = parsed.get(key)
            if isinstance(v, str) and v.strip():
                return " ".join(v.split())[:200]

    for line in raw_text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("---"):
            return line[:200]

    return "(no summary extracted)"


def load_pill(path: pathlib.Path) -> Pill | None:
    if path.name in GENERATED_FILE_NAMES:
        return None
    if path.suffix not in (".md", ".yaml", ".yml") and not path.name.endswith(".md.done"):
        return None

    raw_text = path.read_text(errors="replace")
    parsed = None
    if path.suffix in (".yaml", ".yml"):
        try:
            loaded = yaml.safe_load(raw_text)
            if isinstance(loaded, dict):
                parsed = loaded
        except yaml.YAMLError:
            parsed = None  # malformed pill -- still indexed, just without parsed metadata

    date = guess_date(path, parsed)
    title = guess_title(path, parsed, raw_text)
    summary = guess_summary(parsed, raw_text)
    return Pill(path, date, title, summary)


def collect_pills() -> list[Pill]:
    pills = []
    for base in CAPSULE_DIRS:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file():
                pill = load_pill(path)
                if pill:
                    pills.append(pill)
    pills.sort(key=lambda p: p.sort_key())
    return pills


def render_index(pills: list[Pill]) -> str:
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Pill Index (generated)",
        "",
        f"Regenerated: {now}",
        "",
        "Auto-generated by `tools/hee-pill-index.py` -- do not hand-edit, "
        "re-run the script instead. Source pills under `state_capsules/` and "
        "`status_capsules/` are untouched by this tool; this is a read-only "
        "index over them, not a rewrite. Per "
        "[human-execution-engine#225](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/issues/225).",
        "",
        f"{len(pills)} pills indexed, chronological, oldest first "
        "(pills with no extractable date sort last, not first).",
        "",
    ]
    for pill in pills:
        rel = pill.path.relative_to(REPO_ROOT)
        lines.append(f"## {pill.date} — {pill.title}")
        lines.append("")
        lines.append(f"`{rel}`")
        lines.append("")
        lines.append(pill.summary)
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write docs/history/PILL_INDEX.md instead of printing")
    args = parser.parse_args()

    pills = collect_pills()
    output = render_index(pills)

    if args.write:
        OUTPUT_PATH.write_text(output)
        print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(pills)} pills)", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
