"""hee_inv -- inventory records rendered from documents.

The contract is hee/contracts/inventory.contract.v1.md. This module is the
writer behind ``hee inv add``: one ``hee.inventory.asset-request.v1`` JSON
document in, one ``inventory.asset`` Measure out. The same document is what
the inventory page's add form submits, so a record typed at a shell and a
record submitted from a browser are validated by the same code.

The allowed values of inv.sub, inv.bucket and inv.lifecycle are READ FROM
THE CONTRACT, not copied here. A second list in code is a list that drifts:
inv.sub gained ``electronics`` on 2026-09-12, and a copy made the day before
would have refused every drive and computer with a reason that looked right.

YAML is rendered by hand, deterministically, with every string written as a
JSON string. A JSON string is a valid YAML double-quoted scalar, so this
needs no YAML library to write and cannot emit a bare ``no`` or ``on`` that a
reader turns into a boolean.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "hee.inventory.asset-request.v1"
MAX_BYTES = 16384
SOA_REF = "~/.hee/index/_.yaml#hee-soa.v1"
ORIGIN_SLUG = "Twin-Cities-Open-Systems/tcos-plan-private"

TOKEN = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
PATH_PART = re.compile(r"^[A-Za-z0-9._-]{1,40}$")
MAC = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")
OBSERVED = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ROLES = ("wired", "wireless")

REQUIRED = ("schema", "name", "asset_type", "sub", "bucket", "lifecycle")
OPTIONAL = ("stableid", "vendor", "model", "serial", "interfaces", "location",
            "specs", "requirements", "refs", "notes", "source", "observed")

CONTRACT = Path(__file__).resolve().parents[3] / "hee" / "contracts" / "inventory.contract.v1.md"


class Invalid(ValueError):
    """The document breaks the contract: CRITICAL."""


class Unusable(RuntimeError):
    """The tool cannot determine anything -- no contract, no repo: UNKNOWN."""


def contract_values(path: Path = CONTRACT) -> dict:
    """{'inv.sub': [...], 'inv.bucket': [...], 'inv.lifecycle': [...]} from the contract's taxonomy lines."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise Unusable(f"cannot read the inventory contract at {path}: {e.strerror}") from e
    out = {}
    for label in ("inv.sub", "inv.bucket", "inv.lifecycle"):
        m = re.search(r"^- " + re.escape(label) + r":\s*([^\n(]+)", text, re.M)
        if not m:
            raise Unusable(f"the inventory contract has no '- {label}:' line")
        out[label] = [v.strip() for v in m.group(1).split("|") if v.strip()]
    return out


def _text(doc, key, maxlen, required=False):
    v = doc.get(key)
    if v is None:
        if required:
            raise Invalid(f"{key}: required")
        return None
    if not isinstance(v, str):
        raise Invalid(f"{key}: must be a string{'' if required else ' or null'}")
    v = v.strip()
    if not v:
        if required:
            raise Invalid(f"{key}: required, and empty")
        return None
    if len(v) > maxlen:
        raise Invalid(f"{key}: over {maxlen} characters")
    if key != "notes" and ("\n" in v or "\r" in v):
        raise Invalid(f"{key}: one line only")
    return v


def _choice(doc, key, allowed):
    v = _text(doc, key, 40, required=True)
    if v not in allowed:
        raise Invalid(f"{key}: '{v}' is not one of {' | '.join(allowed)} (from the contract)")
    return v


def _strings(doc, key, maxlen, maxitems):
    v = doc.get(key)
    if v is None:
        return []
    if not isinstance(v, list) or len(v) > maxitems:
        raise Invalid(f"{key}: must be a list of at most {maxitems} strings")
    out = []
    for i, s in enumerate(v):
        if not isinstance(s, str) or not s.strip() or len(s) > maxlen or "\n" in s:
            raise Invalid(f"{key}[{i}]: must be a one-line string of 1-{maxlen} characters")
        out.append(s.strip())
    return out


def tsz(observed: str) -> str:
    """2026-09-12T06:20:50Z -> 20260912t062050z, the contract's compact form."""
    return observed.replace("-", "").replace(":", "").lower()


def validate(doc, values: dict, now: datetime | None = None) -> dict:
    """A checked, normalized request. Raises Invalid with the first reason found."""
    if not isinstance(doc, dict):
        raise Invalid("the document must be a JSON object")
    unknown = sorted(set(doc) - set(REQUIRED) - set(OPTIONAL))
    if unknown:
        raise Invalid(f"unknown field(s): {', '.join(unknown)}")
    if doc.get("schema") != SCHEMA:
        raise Invalid(f"schema: must be {SCHEMA}")

    r = {
        "name": _text(doc, "name", 80, required=True),
        "asset_type": _text(doc, "asset_type", 40, required=True),
        "sub": _choice(doc, "sub", values["inv.sub"]),
        "bucket": _choice(doc, "bucket", values["inv.bucket"]),
        "lifecycle": _choice(doc, "lifecycle", values["inv.lifecycle"]),
        "vendor": _text(doc, "vendor", 80),
        "model": _text(doc, "model", 120),
        "serial": _text(doc, "serial", 120),
        "notes": _text(doc, "notes", 2000),
        "requirements": _strings(doc, "requirements", 300, 30),
        "refs": _strings(doc, "refs", 500, 20),
    }
    if not TOKEN.match(r["asset_type"]):
        raise Invalid("asset_type: lowercase letters, digits and dashes, starting with a letter or digit, at most 40")
    for i, ref in enumerate(r["refs"]):
        if not ref.startswith("https://"):
            raise Invalid(f"refs[{i}]: must be an https:// URL")

    observed = doc.get("observed")
    if observed is None:
        observed = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif not isinstance(observed, str) or not OBSERVED.match(observed):
        raise Invalid("observed: must be UTC in the form 2026-09-12T06:20:50Z")
    r["observed"] = observed

    interfaces = doc.get("interfaces") or []
    if not isinstance(interfaces, list) or len(interfaces) > 8:
        raise Invalid("interfaces: must be a list of at most 8")
    r["interfaces"] = []
    for i, itf in enumerate(interfaces):
        if not isinstance(itf, dict) or set(itf) - {"role", "mac"}:
            raise Invalid(f"interfaces[{i}]: must be an object with role and mac")
        role, mac = itf.get("role"), itf.get("mac")
        if role not in ROLES:
            raise Invalid(f"interfaces[{i}].role: must be {' or '.join(ROLES)}")
        mac = mac.strip().lower().replace("-", ":") if isinstance(mac, str) else ""
        if not MAC.match(mac):
            raise Invalid(f"interfaces[{i}].mac: must be six hex pairs, like b8:27:eb:a7:84:61")
        r["interfaces"].append({"role": role, "mac": mac})

    loc = doc.get("location")
    r["location"] = []
    if loc is not None:
        path = loc.get("path") if isinstance(loc, dict) and set(loc) <= {"path"} else None
        if not isinstance(path, list) or not 1 <= len(path) <= 8 or \
                not all(isinstance(p, str) and PATH_PART.match(p) for p in path):
            raise Invalid("location.path: 1-8 parts of letters, digits, dot, dash or underscore")
        r["location"] = path

    specs = doc.get("specs")
    r["specs"] = {}
    if specs is not None:
        if not isinstance(specs, dict) or len(specs) > 60:
            raise Invalid("specs: must be an object of at most 60 fields")
        for k, v in specs.items():
            if not isinstance(k, str) or not TOKEN.match(k.replace("_", "-")):
                raise Invalid(f"specs.{k}: keys are lowercase tokens (letters, digits, dash, underscore)")
            if not isinstance(v, str) or not v.strip() or len(v) > 300 or "\n" in v:
                raise Invalid(f"specs.{k}: values are one-line strings of 1-300 characters")
            r["specs"][k] = v.strip()

    src = doc.get("source")
    r["source"] = {}
    if src is not None:
        if not isinstance(src, dict) or len(src) > 10:
            raise Invalid("source: must be an object of at most 10 fields")
        for k, v in src.items():
            if not TOKEN.match(k.replace("_", "-")) or not isinstance(v, str) or len(v) > 500:
                raise Invalid(f"source.{k}: keys are tokens, values strings of at most 500 characters")
            r["source"][k] = v

    r["stableid"] = stableid(doc.get("stableid"), r["serial"], r["asset_type"], observed)
    return r


def stableid(given, serial, asset_type, observed) -> str:
    """The contract's order: an assigned id, else the serial, else asset_type-tsz."""
    if given is not None:
        if not isinstance(given, str) or not TOKEN.match(given):
            raise Invalid("stableid: lowercase letters, digits and dashes, starting with a letter or digit, at most 40")
        return given
    if serial:
        slug = re.sub(r"[^a-z0-9]+", "-", serial.lower()).strip("-")[:40].strip("-")
        if TOKEN.match(slug):
            return slug
    return f"{asset_type}-{tsz(observed)}"[:40].rstrip("-")


def q(v) -> str:
    return "null" if v is None else json.dumps(v, ensure_ascii=False)


def render(r: dict) -> tuple[str, str]:
    """(metadata.name, YAML text) for a validated request."""
    name = f"inv-asset-{r['sub']}-{r['stableid']}"
    y = [
        "apiVersion: hee/v1",
        "kind: Measure",
        "metadata:",
        f"  name: {name}",
        "  labels:",
        '    hee.object: "true"',
        "    hee.tcos/topic: inventory",
        f"    inv.bucket: {r['bucket']}",
        f"    inv.sub: {r['sub']}",
        f"    inv.lifecycle: {r['lifecycle']}",
    ]
    y += [f"    inv.loc{i}: {q(p)}" for i, p in enumerate(r["location"][:4])]
    y += [
        "spec:",
        "  measure: inventory.asset",
        "  context:",
        "    soa:",
        f"      file_ref: {q(SOA_REF)}",
        "    evidence: []",
        "  ts:",
        f"    observed: {q(r['observed'])}",
    ]
    if r["location"]:
        y += ["  location:", f"    path: [{', '.join(q(p) for p in r['location'])}]"]
    if r["source"]:
        y += ["  source:"] + [f"    {k}: {q(v)}" for k, v in r["source"].items()]
    y += [
        "  asset:",
        f"    name: {q(r['name'])}",
        f"    asset_type: {r['asset_type']}",
        f"    lifecycle: {r['lifecycle']}",
        f"    stableid: {r['stableid']}",
        f"    vendor: {q(r['vendor'])}",
        f"    model: {q(r['model'])}",
        f"    serial: {q(r['serial'])}",
    ]
    if r["specs"]:
        y += ["    specs:"] + [f"      {k}: {q(v)}" for k, v in r["specs"].items()]
    else:
        y += ["    specs: {}"]
    if r["interfaces"]:
        y += ["    interfaces:"]
        for itf in r["interfaces"]:
            y += [f"      - role: {itf['role']}", f"        mac: {q(itf['mac'])}"]
    else:
        y += ["    interfaces: []"]
    for key in ("requirements", "refs"):
        y += [f"    {key}:"] + [f"      - {q(s)}" for s in r[key]] if r[key] else [f"    {key}: []"]
    y += [f"    notes: {q(r['notes'])}"]
    return name, "\n".join(y) + "\n"


def repo_guard(repo: Path) -> Path:
    """The dataset repo, resolved -- or Unusable. Same checks as hee-inv's repo_guard_tcos."""
    repo = repo.resolve()
    top = subprocess.run(["git", "-C", str(repo), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0:
        raise Unusable(f"not a git repository: {repo}")
    if Path(top.stdout.strip()).resolve() != repo:
        raise Unusable(f"not the top of a repository: {repo} (top is {top.stdout.strip()})")
    origin = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"], capture_output=True, text=True)
    if origin.returncode != 0 or ORIGIN_SLUG not in origin.stdout:
        raise Unusable(f"origin is not {ORIGIN_SLUG}: {origin.stdout.strip() or 'no origin remote'}")
    return repo


def add(doc_bytes: bytes, repo: Path, dry_run: bool = False, home: str | None = None) -> tuple[str, str]:
    """Validate, render and write one record. Returns (repo-relative path, YAML)."""
    anchor = Path(home or os.path.expanduser("~")) / ".hee" / "index" / "_.yaml"
    if not anchor.is_file():
        raise Unusable(f"missing SOA anchor: {anchor}")
    if len(doc_bytes) > MAX_BYTES:
        raise Invalid(f"the document is over {MAX_BYTES} bytes")
    try:
        doc = json.loads(doc_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise Invalid(f"not valid UTF-8 JSON: {e}") from e
    r = validate(doc, contract_values())
    repo = repo_guard(repo)
    name, text = render(r)
    objdir = repo / "inventory" / "objects" / "asset"
    existing = sorted(objdir.glob(f"*__{name}.yaml")) if objdir.is_dir() else []
    if existing:
        raise Invalid(f"{name} already exists: {existing[0].relative_to(repo)}")
    rel = f"inventory/objects/asset/{tsz(r['observed'])}__{name}.yaml"
    if not dry_run:
        objdir.mkdir(parents=True, exist_ok=True)
        tmp = repo / (rel + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, repo / rel)
    return rel, text
