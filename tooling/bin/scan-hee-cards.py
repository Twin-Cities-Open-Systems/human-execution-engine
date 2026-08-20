#!/usr/bin/env python3
"""scan-hee-cards.py -- tolerant inventory of hee/cards/*.

Prior scanners here reportedly kept failing. The likely reason, found by
actually reading ~20 real files first instead of assuming a schema:
the directory is NOT homogeneous. It mixes:
  - kind: Card (the majority)
  - kind: Pill (at least one -- uiboss-repohub-next.wip.yaml)
  - kind: GreenCard (a template placeholder, lives elsewhere but same shape)
  - plain .md files with no YAML frontmatter at all (gpt-prompting-guide.md,
    handoff..pr.134.v2.md)
  - .yaml files with no apiVersion/kind at all (editor.vscode-specials.yaml)
  - detached PGP signature files that happen to end in .yaml
    (spencer-blank-generation-lyric.card.v1.yaml.asc and .yaml.spencer.asc)
  - completely freeform `spec:` shapes -- there is no fixed sub-schema

So: this scanner never assumes a shape. It classifies what each file
actually is, reports parse failures as data (not crashes), and never
requires a specific field to exist before reporting on the file.

Usage: scan-hee-cards.py <dir> [--json]
"""
import sys
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Needs PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def classify(path: Path) -> dict:
    entry = {"file": path.name, "size": path.stat().st_size}

    # Detached signatures aren't content at all -- don't even try to parse.
    if path.suffix == ".asc" or path.name.endswith(".asc"):
        entry["type"] = "detached-signature"
        return entry

    raw = path.read_text(errors="replace")

    if path.suffix == ".md":
        entry["type"] = "markdown-doc"
        entry["note"] = "not a YAML object, plain doc"
        return entry

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        entry["type"] = "parse-error"
        entry["error"] = str(e).splitlines()[0]
        return entry

    if not isinstance(data, dict):
        entry["type"] = "yaml-not-a-mapping"
        return entry

    api_version = data.get("apiVersion")
    kind = data.get("kind")

    if not api_version and not kind:
        entry["type"] = "yaml-no-hee-object"
        entry["note"] = "valid YAML, but no apiVersion/kind -- not a HEE object"
        return entry

    entry["type"] = "hee-object"
    entry["apiVersion"] = api_version
    entry["kind"] = kind
    meta = data.get("metadata") or {}
    entry["name"] = meta.get("name")
    entry["description"] = meta.get("description")
    spec = data.get("spec") or {}
    entry["status"] = spec.get("status")
    # needs_dif shows up both top-level and under spec across the real files
    entry["needs_dif"] = bool(data.get("needs_dif") or spec.get("needs_dif"))
    return entry


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    as_json = "--json" in sys.argv
    target = Path([a for a in sys.argv[1:] if a != "--json"][0])

    results = [classify(p) for p in sorted(target.iterdir()) if p.is_file()]

    if as_json:
        print(json.dumps(results, indent=2))
        return

    by_type = {}
    for r in results:
        by_type.setdefault(r["type"], []).append(r)

    print(f"=== {target} -- {len(results)} files ===\n")

    kinds = [r for r in results if r["type"] == "hee-object"]
    by_kind = {}
    for r in kinds:
        by_kind.setdefault(r.get("kind") or "(no kind)", []).append(r)

    for kind, items in sorted(by_kind.items()):
        print(f"kind: {kind}  ({len(items)})")
        for r in items:
            flags = []
            if r.get("needs_dif"):
                flags.append("needs_dif")
            if r.get("status"):
                flags.append(f"status={r['status']}")
            flag_str = f"  [{', '.join(flags)}]" if flags else ""
            print(f"  {r['file']}{flag_str}")
        print()

    for t in ("parse-error", "yaml-not-a-mapping", "yaml-no-hee-object", "markdown-doc", "detached-signature"):
        items = by_type.get(t, [])
        if not items:
            continue
        print(f"{t}  ({len(items)})")
        for r in items:
            extra = f" -- {r['error']}" if r.get("error") else ""
            print(f"  {r['file']}{extra}")
        print()


if __name__ == "__main__":
    main()
