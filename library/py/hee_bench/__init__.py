"""hee_bench -- judge a model against this org's own work, not a leaderboard.

HEE#361, operator 2026-08-24: "we only care about LLMs and models acting
against things we care about, not some broad marketing benchmark." So a
bench here is a directory of CASES, each one drawn from real work this org
already did and graded against what the org actually valued in the outcome.
The tool in ``tooling/bin/hee-bench`` is a thin CLI over this module; every
grader is deterministic and runs with no network, so a saved run can be
re-graded offline when a grader changes.

Five kinds of case, each with a grader that needs no judgement of its own:

``predicate``    the answer's first word is YES or NO
``choice``       the answer's first word is one of a fixed list
``set``          the answer is a comma-separated list, compared as a set
``exact``        the answer equals a string (whitespace and case folded)
``no_invented``  the answer names no host, URL, address or vmid that the
                 prompt did not supply -- the failure llm-1 showed on its
                 first real task (fleet-ops pve/upgrade-2026-10/README.md):
                 it ordered dependencies well and invented the specifics

Scoring borrows HEE#326's RPN (severity x occurrence x detection) instead of
inventing a new scheme. A case declares ``severity`` (what a wrong answer
costs where this gate sits) and ``detection`` (how likely a wrong answer
slips past whatever checks it downstream; 10 = never caught). ``occurrence``
is MEASURED: the failure rate over the run's repeats, on a 0..10 scale. A
case that always passes scores 0; the run's RPN is the sum.

The endpoint is anything OpenAI-compatible (``/v1/chat/completions``):
llama.cpp's ``llama-server``, Ollama, vLLM. Requests go at temperature 0, so
a run is as reproducible as the server allows.

Nothing about a particular fleet lives here: which endpoint, which cases and
where the results are kept are the caller's (``HEE_BENCH_ENDPOINT``,
``HEE_BENCH_CASES``, ``--out``), never a path baked into this module.
"""

from __future__ import annotations

import json
import math
import re
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

__all__ = [
    "DEFAULT_MAX_TOKENS",
    "KINDS",
    "SCHEMA_VERSION",
    "BenchError",
    "chat",
    "collapse",
    "first_word",
    "grade",
    "load_cases",
    "load_run",
    "occurrence",
    "regrade",
    "report_md",
    "rpn",
    "run",
    "save",
    "served_model",
    "specifics",
    "split_items",
    "strip_thinking",
    "summarize",
    "utcnow",
    "validate_case",
]

SCHEMA_VERSION = 1
KINDS = ("predicate", "choice", "set", "exact", "no_invented")
DEFAULT_MAX_TOKENS = {"predicate": 8, "choice": 8, "set": 64, "exact": 64, "no_invented": 1024}
CASE_KEYS = {"kind", "source", "system", "prompt", "expected", "choices", "allowed",
             "max_tokens", "severity", "detection", "why", "name"}


class BenchError(Exception):
    """A refusal: bad case, bad run file, unreachable endpoint."""


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------
# cases
# --------------------------------------------------------------------------

def _int_in(raw: dict, key: str, default: int, lo: int, hi: int, where: str) -> int:
    v = raw.get(key, default)
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise BenchError(f"{where}: {key} must be an integer {lo}..{hi}, got {v!r}")
    return v


def validate_case(raw, name: str, where: str = "") -> dict:
    """Check one case mapping and return it normalized. Refuses loudly."""
    where = where or name
    if not isinstance(raw, dict):
        raise BenchError(f"{where}: a case is a mapping, not {type(raw).__name__}")
    unknown = sorted(set(raw) - CASE_KEYS)
    if unknown:
        raise BenchError(f"{where}: unknown key(s) {', '.join(unknown)}")
    kind = raw.get("kind")
    if kind not in KINDS:
        raise BenchError(f"{where}: kind must be one of {', '.join(KINDS)}, got {kind!r}")
    prompt = raw.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise BenchError(f"{where}: prompt is required")
    source = raw.get("source")
    if not isinstance(source, str) or not source.strip():
        raise BenchError(f"{where}: source is required -- every case names the real work it came from")
    system = raw.get("system", "")
    if system is None:
        system = ""
    if not isinstance(system, str):
        raise BenchError(f"{where}: system must be a string")
    case = {
        "name": str(raw.get("name") or name),
        "kind": kind,
        "source": source.strip(),
        "system": system,
        "prompt": prompt,
        "max_tokens": _int_in(raw, "max_tokens", DEFAULT_MAX_TOKENS[kind], 1, 32768, where),
        "severity": _int_in(raw, "severity", 5, 1, 10, where),
        "detection": _int_in(raw, "detection", 5, 1, 10, where),
        "why": str(raw.get("why") or ""),
        "choices": None,
        "allowed": [],
        "expected": None,
    }
    exp = raw.get("expected")
    if isinstance(exp, bool) and kind == "predicate":
        exp = "YES" if exp else "NO"      # YAML 1.1 reads a bare YES/NO as a boolean; that spelling is fine
    if kind == "predicate":
        if not isinstance(exp, str) or exp.strip().upper() not in ("YES", "NO"):
            raise BenchError(f"{where}: a predicate's expected is YES or NO, got {exp!r}")
        case["expected"] = exp.strip().upper()
    elif kind == "choice":
        choices = raw.get("choices")
        if not isinstance(choices, list) or len(choices) < 2 or not all(isinstance(c, str) and c.strip() for c in choices):
            raise BenchError(f"{where}: a choice needs choices: a list of at least two strings")
        case["choices"] = [c.strip() for c in choices]
        if not isinstance(exp, str) or exp.strip().upper() not in {c.upper() for c in case["choices"]}:
            raise BenchError(f"{where}: expected {exp!r} is not one of the choices")
        case["expected"] = exp.strip()
    elif kind == "set":
        if not isinstance(exp, list) or not all(isinstance(e, str) for e in exp):
            raise BenchError(f"{where}: a set's expected is a list of strings (empty means NONE)")
        case["expected"] = [e.strip() for e in exp if e.strip()]
    elif kind == "exact":
        if not isinstance(exp, str):
            raise BenchError(f"{where}: an exact's expected is a string")
        case["expected"] = exp
    elif kind == "no_invented":
        if exp is not None:
            raise BenchError(f"{where}: no_invented takes no expected; the prompt is the allow-list")
        allowed = raw.get("allowed") or []
        if not isinstance(allowed, list) or not all(isinstance(a, str) for a in allowed):
            raise BenchError(f"{where}: allowed is a list of strings")
        case["allowed"] = [a.strip() for a in allowed if a.strip()]
    if kind != "no_invented" and raw.get("allowed"):
        raise BenchError(f"{where}: allowed applies only to no_invented")
    if kind != "choice" and raw.get("choices"):
        raise BenchError(f"{where}: choices applies only to choice")
    return case


def load_cases(cases_dir, only=None) -> list[dict]:
    """Every ``*.yaml`` under the directory, one case per file, by name."""
    d = Path(cases_dir).expanduser()
    if not d.is_dir():
        raise BenchError(f"no cases directory {d}")
    cases = []
    for p in sorted(d.glob("*.yaml")):
        with open(p, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        case = validate_case(raw, p.stem, where=str(p))
        case["file"] = str(p)
        if only and case["name"] not in only:
            continue
        cases.append(case)
    if only:
        missing = sorted(set(only) - {c["name"] for c in cases})
        if missing:
            raise BenchError(f"no such case(s) in {d}: {', '.join(missing)}")
    if not cases:
        raise BenchError(f"no *.yaml cases in {d}")
    return cases


# --------------------------------------------------------------------------
# graders -- deterministic, no network
# --------------------------------------------------------------------------

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
_WORD = re.compile(r"[A-Za-z0-9_-]+")
_URL = re.compile(r"https?://[^\s)>\]'\"`]+", re.IGNORECASE)
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_VMID = re.compile(r"\bct\d{3}\b", re.IGNORECASE)
_HOST = re.compile(r"\b[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+\b", re.IGNORECASE)
# A dotted name whose last label is one of these is a FILE, not a host.
_FILE_SUFFIXES = {"gpg", "asc", "conf", "cfg", "yaml", "yml", "json", "md", "txt", "log", "sh",
                  "py", "pl", "service", "timer", "list", "sources", "gz", "xz", "zst", "tar",
                  "tsv", "csv", "html", "css", "js", "img", "iso", "deb", "rpm", "key", "pem",
                  "crt", "gguf", "bin", "env", "d", "so"}


def strip_thinking(text: str) -> str:
    """Drop a ``<think>...</think>`` trace if the server let one through."""
    return _THINK.sub("", text or "").strip()


def first_word(text: str) -> str:
    """The answer's first word, upper-cased: ``"Yes, because"`` -> ``YES``."""
    m = _WORD.search(strip_thinking(text))
    return m.group(0).upper() if m else ""


def split_items(text: str) -> set[str]:
    """A comma/newline/semicolon list as a lower-cased set; ``NONE`` is empty."""
    items = [i.strip().strip(".").strip().lower() for i in re.split(r"[,\n;]+", strip_thinking(text))]
    items = [i for i in items if i]
    if items == ["none"]:
        return set()
    return set(items)


def collapse(text: str) -> str:
    """Whitespace folded, case folded, a trailing period dropped."""
    return " ".join(strip_thinking(text).split()).rstrip(".").lower()


def specifics(text: str) -> set[str]:
    """Every URL, IPv4 address, ``ctNNN`` vmid and dotted hostname in the text.

    A version like ``8.1.3`` is not a host (its last label has no letter);
    ``proxmox-release-bookworm.gpg`` is not a host (its last label is a file
    suffix); ``e.g`` and ``i.e`` are not hosts (no TLD is one letter -- found
    on the first real run, 2026-10-16); a host that is part of a found URL is
    reported once, as the URL.
    """
    t = strip_thinking(text)
    urls = {m.group(0).rstrip(".,;:").lower() for m in _URL.finditer(t)}
    found = set(urls)
    found |= {m.group(0) for m in _IPV4.finditer(t)}
    found |= {m.group(0).lower() for m in _VMID.finditer(t)}
    for m in _HOST.finditer(t):
        h = m.group(0).lower()
        if _IPV4.fullmatch(h):
            continue
        last = h.rsplit(".", 1)[-1]
        # a version (8.1.3) has no letter in its last label; a file (x.gpg) has a suffix; an
        # abbreviation (e.g, i.e, a.m) has a one-letter last label, and no TLD is one letter
        if not re.search(r"[a-z]", last) or len(last) < 2 or last in _FILE_SUFFIXES:
            continue
        if any(h in u for u in urls):
            continue
        found.add(h)
    return found


def _allowed_text(case: dict) -> str:
    return "\n".join([case.get("system") or "", case["prompt"], *(case.get("allowed") or [])]).lower()


def grade(case: dict, answer: str) -> dict:
    """Grade one raw answer: ``{"pass": bool, "got": str, "detail": str}``."""
    kind = case["kind"]
    if kind == "predicate":
        got = first_word(answer)
        return {"pass": got == case["expected"], "got": got, "detail": ""}
    if kind == "choice":
        got = first_word(answer)
        return {"pass": got == case["expected"].upper(), "got": got, "detail": ""}
    if kind == "set":
        got_set = split_items(answer)
        exp = {e.lower() for e in case["expected"]}
        missing = sorted(exp - got_set)
        extra = sorted(got_set - exp)
        detail = "; ".join(p for p in (f"missing {', '.join(missing)}" if missing else "",
                                       f"extra {', '.join(extra)}" if extra else "") if p)
        return {"pass": got_set == exp, "got": ", ".join(sorted(got_set)) or "NONE", "detail": detail}
    if kind == "exact":
        got = collapse(answer)
        return {"pass": got == collapse(case["expected"]), "got": got, "detail": ""}
    if kind == "no_invented":
        allowed = _allowed_text(case)
        invented = sorted(s for s in specifics(answer) if s not in allowed)
        return {"pass": not invented, "got": f"{len(invented)} invented",
                "detail": ", ".join(invented)}
    raise BenchError(f"unknown kind {kind!r}")


# --------------------------------------------------------------------------
# scoring -- HEE#326's RPN, occurrence measured
# --------------------------------------------------------------------------

def occurrence(fails: int, repeats: int) -> int:
    """Failure rate on a 0..10 scale; 0 only when nothing failed."""
    if repeats <= 0:
        raise BenchError("repeats must be positive")
    if fails <= 0:
        return 0
    return max(1, min(10, math.ceil(10 * fails / repeats)))


def rpn(severity: int, occ: int, detection: int) -> int:
    return severity * occ * detection


# --------------------------------------------------------------------------
# the endpoint
# --------------------------------------------------------------------------

def _messages(case: dict) -> list[dict]:
    msgs = []
    if case.get("system"):
        msgs.append({"role": "system", "content": case["system"]})
    msgs.append({"role": "user", "content": case["prompt"]})
    return msgs


def request_body(case: dict, model: str = "default") -> dict:
    return {"model": model, "temperature": 0, "max_tokens": case["max_tokens"],
            "messages": _messages(case)}


def chat(endpoint: str, case: dict, model: str = "default", timeout: float = 120) -> dict:
    """One completion at temperature 0; the raw text plus what the server measured."""
    url = endpoint.rstrip("/") + "/v1/chat/completions"
    req = urllib.request.Request(url, json.dumps(request_body(case, model)).encode(),
                                 {"content-type": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise BenchError(f"{url}: HTTP {e.code} {e.reason}") from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise BenchError(f"{url}: {getattr(e, 'reason', e)}") from e
    ms = round((time.monotonic() - t0) * 1000, 1)
    try:
        choice = data["choices"][0]
        content = choice["message"].get("content") or ""
    except (KeyError, IndexError, TypeError) as e:
        raise BenchError(f"{url}: no choices[0].message.content in the reply") from e
    timings = data.get("timings") or {}
    usage = data.get("usage") or {}
    return {
        "raw": content,
        "latency_ms": ms,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "tok_per_s": timings.get("predicted_per_second"),
        "finish_reason": choice.get("finish_reason"),
    }


def served_model(endpoint: str, timeout: float = 10) -> str:
    """What ``/v1/models`` says is loaded; ``""`` when it will not say."""
    try:
        with urllib.request.urlopen(endpoint.rstrip("/") + "/v1/models", timeout=timeout) as r:
            data = json.load(r)
        rows = data.get("data") or data.get("models") or []
        first = rows[0] if rows else {}
        return str(first.get("id") or first.get("name") or first.get("model") or "")
    except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
        return ""


# --------------------------------------------------------------------------
# a run, and re-grading a saved one
# --------------------------------------------------------------------------

_CASE_FIELDS = ("name", "kind", "source", "system", "prompt", "expected", "choices", "allowed",
                "max_tokens", "severity", "detection", "why")


def _record(case: dict, attempts: list[dict]) -> dict:
    fails = sum(1 for a in attempts if not a["pass"])
    occ = occurrence(fails, len(attempts))
    rec = {k: case.get(k) for k in _CASE_FIELDS}
    rec.update({
        "attempts": attempts,
        "repeats": len(attempts),
        "fails": fails,
        "occurrence": occ,
        "rpn": rpn(case["severity"], occ, case["detection"]),
        "pass": fails == 0,
    })
    return rec


def run(cases: list[dict], endpoint: str, *, model: str = "default", repeats: int = 1,
        timeout: float = 120, log=None) -> dict:
    """Ask every case ``repeats`` times, grade each answer, score the run."""
    if repeats < 1:
        raise BenchError("repeats must be at least 1")
    started = utcnow()
    served = served_model(endpoint, timeout=min(timeout, 10))
    results = []
    for case in cases:
        attempts = []
        for i in range(repeats):
            r = chat(endpoint, case, model=model, timeout=timeout)
            g = grade(case, r["raw"])
            attempts.append({**r, **g})
            if log:
                mark = "ok  " if g["pass"] else "FAIL"
                tail = f" ({g['detail']})" if g["detail"] and not g["pass"] else ""
                log(f"{mark} {case['name']}: {g['got']!r}{tail}  {r['latency_ms']:.0f} ms")
        results.append(_record(case, attempts))
    return {
        "hee_bench": SCHEMA_VERSION,
        "endpoint": endpoint,
        "model": model,
        "served_model": served,
        "started_utc": started,
        "finished_utc": utcnow(),
        "repeats": repeats,
        "results": results,
        "summary": summarize(results),
    }


def regrade(saved: dict) -> dict:
    """Re-apply today's graders to a saved run's raw answers. No network."""
    if not isinstance(saved, dict) or saved.get("hee_bench") != SCHEMA_VERSION:
        raise BenchError(f"not a hee-bench run file (hee_bench: {SCHEMA_VERSION})")
    results = []
    for old in saved.get("results") or []:
        case = validate_case({k: old.get(k) for k in _CASE_FIELDS if old.get(k) not in (None, [], "")
                              or k in ("prompt", "source", "kind")}, old.get("name") or "?")
        attempts = []
        for a in old.get("attempts") or []:
            g = grade(case, a.get("raw") or "")
            attempts.append({**{k: a.get(k) for k in ("raw", "latency_ms", "prompt_tokens",
                                                      "completion_tokens", "tok_per_s", "finish_reason")},
                             **g})
        results.append(_record(case, attempts))
    out = dict(saved)
    out["results"] = results
    out["summary"] = summarize(results)
    out["regraded_utc"] = utcnow()
    return out


def summarize(results: list[dict]) -> dict:
    cases = len(results)
    passed = sum(1 for r in results if r["pass"])
    tps = [a["tok_per_s"] for r in results for a in r["attempts"] if a.get("tok_per_s")]
    lat = [a["latency_ms"] for r in results for a in r["attempts"] if a.get("latency_ms") is not None]
    worst = sorted((r for r in results if not r["pass"]), key=lambda r: (-r["rpn"], r["name"]))
    return {
        "cases": cases,
        "passed": passed,
        "failed": cases - passed,
        "rpn_total": sum(r["rpn"] for r in results),
        "rpn_ceiling": sum(r["severity"] * 10 * r["detection"] for r in results),
        "latency_ms_total": round(sum(lat), 1) if lat else None,
        "tok_per_s_median": round(statistics.median(tps), 1) if tps else None,
        "worst": [{"name": r["name"], "rpn": r["rpn"]} for r in worst[:5]],
    }


def save(run_dict: dict, path) -> Path:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(run_dict, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    return p


def load_run(path) -> dict:
    p = Path(path).expanduser()
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BenchError(f"{p}: {e}") from e
    if not isinstance(data, dict) or data.get("hee_bench") != SCHEMA_VERSION:
        raise BenchError(f"{p}: not a hee-bench run file (hee_bench: {SCHEMA_VERSION})")
    return data


# --------------------------------------------------------------------------
# report: runs side by side -- models against each other, or one over time
# --------------------------------------------------------------------------

def _run_label(r: dict) -> str:
    model = (r.get("served_model") or r.get("model") or "?").rsplit("/", 1)[-1]
    return f"{model} @ {str(r.get('started_utc') or '')[:16]}"


def report_md(runs: list[dict]) -> str:
    """A Markdown table: one row per case, one column per run; totals first."""
    if not runs:
        raise BenchError("report needs at least one run")
    labels = [_run_label(r) for r in runs]
    by_run = [{res["name"]: res for res in r.get("results") or []} for r in runs]
    names = sorted({n for m in by_run for n in m})
    sev = {n: next(m[n] for m in by_run if n in m) for n in names}
    lines = ["| case | S | D | " + " | ".join(labels) + " |",
             "| --- | ---: | ---: | " + " | ".join("---" for _ in labels) + " |"]

    def cell(res):
        if res is None:
            return "-"
        if res["pass"]:
            return "ok"
        return f"FAIL rpn {res['rpn']}"

    for n in names:
        row = [cell(m.get(n)) for m in by_run]
        lines.append(f"| {n} | {sev[n]['severity']} | {sev[n]['detection']} | " + " | ".join(row) + " |")
    s = [r.get("summary") or summarize(r.get("results") or []) for r in runs]
    lines.append("| **passed** | | | " + " | ".join(f"{x['passed']}/{x['cases']}" for x in s) + " |")
    lines.append("| **RPN** (lower is better) | | | " + " | ".join(f"{x['rpn_total']} of {x['rpn_ceiling']}" for x in s) + " |")
    lines.append("| median tok/s | | | " + " | ".join(str(x["tok_per_s_median"] if x["tok_per_s_median"] is not None else "-") for x in s) + " |")
    lines.append("| total latency | | | " + " | ".join(f"{x['latency_ms_total'] / 1000:.1f} s" if x["latency_ms_total"] is not None else "-" for x in s) + " |")
    return "\n".join(lines)
