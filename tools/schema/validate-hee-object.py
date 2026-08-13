#!/usr/bin/env python3
"""validate-hee-object: validate a HEE object YAML file against the
canonical envelope schema (schemas/hee/v1/hee-object.schema.json),
optionally the strict overlay too.

Fills a real gap: ci/doctrine/validate_doctrine.py checks YAML syntax
and file existence only -- it never actually calls jsonschema against
the envelope schema, despite jsonschema being a listed CI dependency.
Existing contract files (roles-trilateral-v1, hee-schema-id-v1) predate
this schema and do not use its apiVersion/kind/metadata envelope --
this tool is what actually proves whether new HEE objects conform,
since nothing currently does.

Follows the repo's own evidence-capture convention (see
tools/schema/schema-id-scan.sh): writes a timestamped, host-stamped
evidence file under .hee/evidence/$TOPIC/, not just stdout.

Usage:
  validate-hee-object.py <file.yaml> [--strict] [--schema PATH]
"""
import argparse
import datetime
import json
import pathlib
import socket
import subprocess
import sys

import yaml
from jsonschema import Draft7Validator, RefResolver


def repo_root() -> pathlib.Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return pathlib.Path(out.stdout.strip())
    except Exception:
        return pathlib.Path.cwd()


def load_schema(schema_path: pathlib.Path):
    with open(schema_path) as f:
        return json.load(f)


def validate(obj: dict, schema_path: pathlib.Path):
    schema = load_schema(schema_path)
    resolver = RefResolver(base_uri=schema_path.resolve().as_uri(), referrer=schema)
    validator = Draft7Validator(schema, resolver=resolver)
    return sorted(validator.iter_errors(obj), key=lambda e: list(e.path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="HEE object YAML file to validate")
    ap.add_argument("--strict", action="store_true",
                     help="also validate against hee-object.strict.schema.json")
    ap.add_argument("--schema", default=None,
                     help="override envelope schema path (default: schemas/hee/v1/hee-object.schema.json)")
    ap.add_argument("--topic", default="hee-object-validation",
                     help="evidence subdir under .hee/evidence/ (default: hee-object-validation)")
    args = ap.parse_args()

    root = repo_root()
    target = pathlib.Path(args.file).resolve()
    schema_path = pathlib.Path(args.schema) if args.schema else root / "schemas" / "hee" / "v1" / "hee-object.schema.json"

    with open(target) as f:
        obj = yaml.safe_load(f)

    results = {"base": validate(obj, schema_path)}
    if args.strict:
        strict_path = root / "schemas" / "hee" / "v1" / "hee-object.strict.schema.json"
        results["strict"] = validate(obj, strict_path)

    ok = all(len(errs) == 0 for errs in results.values())

    evdir = root / ".hee" / "evidence" / args.topic
    evdir.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    host = socket.getfqdn()
    outfile = evdir / f"validate-{target.stem}-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.txt"

    with open(outfile, "w") as ev:
        ev.write(f"# NOW (UTC)\n{now}\n")
        ev.write(f"# HOST\n{host}\n")
        ev.write(f"# TARGET\n{target}\n")
        ev.write(f"# SCHEMA\n{schema_path}\n")
        ev.write(f"# RESULT\n{'PASS' if ok else 'FAIL'}\n\n")
        for mode, errs in results.items():
            ev.write(f"## {mode} ({len(errs)} error(s))\n")
            for e in errs:
                loc = "/".join(str(p) for p in e.path) or "(root)"
                ev.write(f"- {loc}: {e.message}\n")
            ev.write("\n")

    print(f"{'PASS' if ok else 'FAIL'}: {target.name}")
    for mode, errs in results.items():
        if errs:
            print(f"  [{mode}] {len(errs)} error(s):")
            for e in errs:
                loc = "/".join(str(p) for p in e.path) or "(root)"
                print(f"    - {loc}: {e.message}")
    print(f"evidence: {outfile}")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
