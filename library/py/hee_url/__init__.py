"""hee_url -- the URL shortener behind ``hee url``.

Every short link is one HEE object (``apiVersion: hee/v1``, ``kind: Card``)
in a directory of YAML files, one file per slug, so the store is ordinary
tracked git content that ``hee lint`` can check and a diff can review. The
tool in ``tooling/bin/hee-url`` is a thin CLI over this module; everything
that can be tested without a network lives here.

Determinism, on purpose (README: "determinism over convenience"): the slug
is derived from the target URL, so shortening the same URL twice yields the
same slug and the same file, and a record's ``inuid`` reproduces from its
``inuid_seed`` (the short URL itself) exactly as ``hee lint`` demands.

The serving side is a static tree -- a ``_redirects`` file plus one
meta-refresh page per slug -- built from the store by :func:`build`. Any
static host can serve it; :func:`deploy` ships it as a Cloudflare Worker
with static assets, the same way ``tcos-www`` reaches ``tcos.us``.

Configuration is ``~/.config/hee/url.yaml`` (``HEE_URL_CONFIG`` overrides
the path). Every key is optional; :data:`DEFAULTS` lists them all.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

CONFIG_PATH = "~/.config/hee/url.yaml"

# Every key a config file may set, with the value used when it does not.
DEFAULTS: dict = {
    # The public base the short links live under. The hostname is what the
    # Worker's custom domain is attached to.
    "base": "https://u.tcos.us",
    # Where the YAML records live. One file per slug. A relative path is
    # relative to the current directory; ~ expands.
    "store": "~/git/fleet-ops/hee/urls",
    # Slug length, infix included. Must leave at least one free character.
    "length": 8,
    # Text every derived slug must contain. Empty string removes the rule.
    "infix": "goose",
    # Characters a derived slug is built from. Lower-case and digits only, so
    # a slug survives a case-folding proxy and a spoken reading.
    "alphabet": "abcdefghijklmnopqrstuvwxyz0123456789",
    # HTTP status of the redirect. 302 so a retargeted slug is not cached
    # forever by browsers the way a 301 is.
    "status": 302,
    # Cloudflare Worker name the static tree deploys as.
    "worker": "tcos-u",
    "compatibility_date": "2026-08-15",
    # Pinned, like tcos-www/deploy.sh: an unpinned wrangler changed its
    # output format under a grep once already.
    "wrangler": "wrangler@4.86.0",
}

CF_API = "https://api.cloudflare.com/client/v4"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# Names the static host itself owns; a slug may never shadow them.
RESERVED = {"index", "404", "_redirects", "_headers"}


class UrlError(Exception):
    """A user-facing refusal. The CLI prints its text and exits non-zero."""


# --------------------------------------------------------------------------
# configuration


def config_path() -> Path:
    return Path(os.environ.get("HEE_URL_CONFIG") or os.path.expanduser(CONFIG_PATH))


def load_config(path: Path | None = None, overrides: dict | None = None) -> dict:
    """DEFAULTS, then the config file, then explicit overrides (CLI flags).

    Unknown keys in the file are refused rather than ignored: a misspelled
    ``lenght:`` that silently did nothing would look exactly like a config
    that worked.
    """
    cfg = dict(DEFAULTS)
    path = path or config_path()
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        if not isinstance(loaded, dict):
            raise UrlError(f"{path}: expected a mapping of settings")
        unknown = sorted(set(loaded) - set(DEFAULTS))
        if unknown:
            raise UrlError(f"{path}: unknown setting(s) {', '.join(unknown)}; "
                           f"known: {', '.join(sorted(DEFAULTS))}")
        cfg.update(loaded)
    for k, v in (overrides or {}).items():
        if v is not None:
            cfg[k] = v
    validate_config(cfg)
    return cfg


def validate_config(cfg: dict) -> None:
    try:
        cfg["length"] = int(cfg["length"])
        cfg["status"] = int(cfg["status"])
    except (TypeError, ValueError) as e:
        raise UrlError(f"length and status must be integers: {e}") from e
    infix = cfg["infix"] = str(cfg["infix"] or "")
    if infix and not SLUG_RE.match(infix):
        raise UrlError(f"infix {infix!r} must be lower-case letters, digits or '-'")
    if cfg["length"] <= len(infix):
        raise UrlError(f"length {cfg['length']} leaves no room around infix "
                       f"{infix!r} ({len(infix)} chars); raise length or shorten the infix")
    if cfg["status"] not in (301, 302, 307, 308):
        raise UrlError(f"status must be a redirect code (301, 302, 307, 308), not {cfg['status']}")
    if not str(cfg["base"]).startswith(("http://", "https://")):
        raise UrlError(f"base must be an http(s) URL, not {cfg['base']!r}")
    if len(set(cfg["alphabet"])) < 2:
        raise UrlError("alphabet needs at least two distinct characters")


def default_config_text() -> str:
    """The file ``hee url config --init`` writes: every key, commented."""
    lines = ["# hee url -- settings. Every key is optional; these are the defaults.",
             "# See `hee url help` for what each one does.", ""]
    for k, v in DEFAULTS.items():
        lines.append(f"#{k}: {json.dumps(v)}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# slugs


def derive_slug(url: str, cfg: dict, salt: int = 0) -> str:
    """The slug a URL shortens to. Same URL, same slug, on every machine.

    ``length - len(infix)`` characters come from sha256 of the URL, and the
    infix is placed at a position that is itself taken from the hash, so
    ``goose`` does not always sit at the front. ``salt`` is only used to
    step past a slug already taken by a different URL.
    """
    length, infix, alphabet = cfg["length"], cfg["infix"], cfg["alphabet"]
    free = length - len(infix)
    seed = url if salt == 0 else f"{url}\n{salt}"
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    chars = [alphabet[digest[i] % len(alphabet)] for i in range(free)]
    pos = digest[-1] % (free + 1) if infix else 0
    return "".join(chars[:pos]) + infix + "".join(chars[pos:])


def check_slug(slug: str, cfg: dict) -> str:
    """A slug someone chose by hand. Same rules as a derived one, except the
    length, which is theirs to pick."""
    if not SLUG_RE.match(slug):
        raise UrlError(f"slug {slug!r}: lower-case letters, digits and '-' only, starting with a letter or digit")
    if slug in RESERVED:
        raise UrlError(f"slug {slug!r} is reserved by the static host")
    if cfg["infix"] and cfg["infix"] not in slug:
        raise UrlError(f"slug {slug!r} does not contain the required infix {cfg['infix']!r} "
                       f"(set infix: \"\" in {config_path()} to drop the rule)")
    return slug


def check_url(url: str) -> str:
    url = url.strip()
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise UrlError(f"not an http(s) URL: {url!r}")
    if any(c.isspace() for c in url):
        raise UrlError(f"URL contains whitespace: {url!r}")
    return url


# --------------------------------------------------------------------------
# records


def short_url(slug: str, cfg: dict) -> str:
    return f"{str(cfg['base']).rstrip('/')}/{slug}/"


def make_record(slug: str, url: str, cfg: dict, *, tags=(), note: str = "",
                author: str = "", now: str | None = None) -> dict:
    short = short_url(slug, cfg)
    now = now or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    rec = {
        "apiVersion": "hee/v1",
        "kind": "Card",
        "metadata": {
            "name": slug,
            "description": f"short link {short} -> {url}",
            "labels": {"hee.object": "true", "hee.tcos/topic": "url", "artifact": "short-link"},
            "annotations": {
                # hee lint checks that inuid == sha256(inuid_seed).
                "inuid": hashlib.sha256(short.encode("utf-8")).hexdigest(),
                "inuid_seed": short,
                "inuid_derivation": "sha256(inuid_seed)",
                "created_utc": now,
                "author": author or os.environ.get("USER", "unknown"),
            },
        },
        "spec": {
            "slug": slug,
            "short": short,
            "url": url,
            "status": int(cfg["status"]),
            "tags": list(tags),
            "note": note,
        },
    }
    return rec


def dump(rec: dict) -> str:
    return yaml.safe_dump(rec, sort_keys=False, allow_unicode=True, width=1000)


# --------------------------------------------------------------------------
# the store


def store_dir(cfg: dict) -> Path:
    return Path(os.path.expanduser(str(cfg["store"])))


def record_path(slug: str, cfg: dict) -> Path:
    return store_dir(cfg) / f"{slug}.yaml"


def load_all(cfg: dict) -> dict[str, dict]:
    """slug -> record, for every well-formed file in the store."""
    d = store_dir(cfg)
    out: dict[str, dict] = {}
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.yaml")):
        with open(p, encoding="utf-8") as f:
            rec = yaml.safe_load(f)
        if not isinstance(rec, dict) or rec.get("apiVersion") != "hee/v1":
            continue
        spec = rec.get("spec") or {}
        slug = spec.get("slug") or p.stem
        if slug != p.stem:
            raise UrlError(f"{p}: file name and spec.slug disagree ({p.stem} vs {slug})")
        out[slug] = rec
    return out


def load(slug: str, cfg: dict) -> dict | None:
    p = record_path(slug, cfg)
    if not p.is_file():
        return None
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_by_url(url: str, records: dict[str, dict]) -> str | None:
    for slug, rec in records.items():
        if (rec.get("spec") or {}).get("url") == url:
            return slug
    return None


def add(url: str, cfg: dict, *, slug: str | None = None, tags=(), note: str = "",
        author: str = "", force: bool = False) -> tuple[dict, bool]:
    """Shorten ``url``. Returns (record, created).

    Idempotent: a URL already in the store returns its existing record and
    ``created=False`` (unless a different ``slug`` is asked for by hand).
    A derived slug that another URL already holds is stepped past with a
    salt; a hand-picked one that is taken is refused unless ``force``.
    """
    url = check_url(url)
    records = load_all(cfg)
    if slug is None:
        existing = find_by_url(url, records)
        if existing:
            return records[existing], False
        salt = 0
        while True:
            slug = derive_slug(url, cfg, salt)
            if slug not in records or records[slug]["spec"]["url"] == url:
                break
            salt += 1
            if salt > 1000:
                raise UrlError("could not find a free slug after 1000 tries; the store is full at this length")
    else:
        slug = check_slug(slug, cfg)
        taken = records.get(slug)
        if taken and taken["spec"]["url"] == url:
            return taken, False
        if taken and not force:
            raise UrlError(f"slug {slug!r} already points at {taken['spec']['url']} (use --force to retarget)")
    rec = make_record(slug, url, cfg, tags=tags, note=note, author=author)
    d = store_dir(cfg)
    d.mkdir(parents=True, exist_ok=True)
    with open(record_path(slug, cfg), "w", encoding="utf-8") as f:
        f.write(dump(rec))
    return rec, True


def remove(slug: str, cfg: dict) -> dict:
    rec = load(slug, cfg)
    if rec is None:
        raise UrlError(f"no short link {slug!r} in {store_dir(cfg)}")
    record_path(slug, cfg).unlink()
    return rec


def search(terms: list[str], records: dict[str, dict], use_or: bool = False) -> list[str]:
    """Slugs whose url, tags or note match every term (or any, with use_or).
    Case-insensitive substring match -- the SQL LIKE the first version did."""
    hits = []
    for slug, rec in records.items():
        spec = rec.get("spec") or {}
        hay = " ".join([slug, str(spec.get("url", "")), " ".join(spec.get("tags") or []),
                        str(spec.get("note", ""))]).lower()
        found = [t.lower() in hay for t in terms]
        if (any(found) if use_or else all(found)):
            hits.append(slug)
    return hits


# --------------------------------------------------------------------------
# the static tree


_PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={url}">
<link rel="canonical" href="{url}">
<title>{slug}</title>
<p>Redirecting to <a href="{url}">{url}</a>.</p>
"""

_INDEX = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{host}</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 1rem}}</style>
<h1>{host}</h1>
<p>Short links for <a href="https://tcos.us">Twin Cities Open Systems</a>.
A link here looks like <code>{example}</code> and sends you on to the page it stands for.</p>
<p>There is no directory. If you did not get a link from someone, there is nothing to browse.</p>
"""

_404 = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>no such link</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 1rem}}</style>
<h1>No such link</h1>
<p>Nothing on {host} answers to that path. Check the link you were given.</p>
"""


def build(cfg: dict, out: Path, records: dict[str, dict] | None = None) -> list[str]:
    """Write the static tree for the store into ``out``. Returns the slugs.

    ``_redirects`` is what Cloudflare (Pages, and Workers with static assets)
    serves as a real HTTP redirect. ``<slug>/index.html`` is the same
    redirect as a meta refresh, for a host that has no ``_redirects`` and as
    the page a curious person sees. The root page and 404 are fixed text.
    """
    records = load_all(cfg) if records is None else records
    out.mkdir(parents=True, exist_ok=True)
    host = urllib.parse.urlsplit(str(cfg["base"])).netloc
    lines = ["# generated by `hee url build` from the YAML store -- do not edit"]
    for slug in sorted(records):
        spec = records[slug]["spec"]
        url, status = spec["url"], int(spec.get("status") or cfg["status"])
        lines.append(f"/{slug} {url} {status}")
        lines.append(f"/{slug}/ {url} {status}")
        d = out / slug
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(_PAGE.format(url=html.escape(url, quote=True), slug=html.escape(slug)),
                                      encoding="utf-8")
    (out / "_redirects").write_text("\n".join(lines) + "\n", encoding="utf-8")
    example = short_url(derive_slug("https://example.com/", cfg), cfg)
    (out / "index.html").write_text(_INDEX.format(host=html.escape(host), example=html.escape(example)),
                                    encoding="utf-8")
    (out / "404.html").write_text(_404.format(host=html.escape(host)), encoding="utf-8")
    return sorted(records)


# --------------------------------------------------------------------------
# the internet


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe(short: str, timeout: float = 10.0) -> tuple[int | None, str | None, str | None]:
    """(status, location, error) for one short URL, without following it."""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(short, method="HEAD", headers={"User-Agent": "hee-url/verify"})
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.headers.get("Location"), None
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location"), None
    except (urllib.error.URLError, OSError) as e:
        return None, None, str(getattr(e, "reason", e))


def verify(cfg: dict, records: dict[str, dict] | None = None, timeout: float = 10.0) -> list[tuple[str, str, str]]:
    """Ask the live host about every record. Returns (level, slug, detail)
    per record: OK when the server itself redirects to the recorded URL,
    WARNING when the page is served but only the meta refresh would send
    a visitor on, CRITICAL when it points elsewhere or is missing, UNKNOWN
    when the host could not be reached."""
    records = load_all(cfg) if records is None else records
    out = []
    for slug in sorted(records):
        spec = records[slug]["spec"]
        status, loc, err = probe(spec["short"], timeout)
        if err:
            out.append(("UNKNOWN", slug, f"{spec['short']}: {err}"))
        elif status in (301, 302, 307, 308) and loc == spec["url"]:
            out.append(("OK", slug, f"{spec['short']} -> {status} {loc}"))
        elif status in (301, 302, 307, 308):
            out.append(("CRITICAL", slug, f"{spec['short']} -> {status} {loc}, expected {spec['url']}"))
        elif status == 200:
            out.append(("WARNING", slug, f"{spec['short']} served 200 (meta refresh only, no server redirect)"))
        else:
            out.append(("CRITICAL", slug, f"{spec['short']} -> HTTP {status}"))
    return out


def _cf(method: str, path: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{CF_API}{path}", data=data, method=method,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": "application/json",
                                          "User-Agent": "hee-url/deploy"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        try:
            payload = json.load(e)
        except Exception:  # noqa: BLE001
            raise UrlError(f"Cloudflare {method} {path}: HTTP {e.code}") from e
    if not payload.get("success"):
        errs = "; ".join(f"{x.get('code')} {x.get('message')}" for x in payload.get("errors") or [])
        raise UrlError(f"Cloudflare {method} {path}: {errs or 'request failed'}")
    return payload.get("result")


def cf_token() -> str:
    """CLOUDFLARE_API_TOKEN, or HEE_CRED_PASS as `hee cred -pass ... -exec` sets it."""
    tok = os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("HEE_CRED_PASS")
    if not tok:
        raise UrlError("no Cloudflare token: set CLOUDFLARE_API_TOKEN, or run via "
                       "`hee cred -pass cloudflare-tcos-www -dir ~/git/tcos-www/.hee/secrets -exec hee url deploy`")
    return tok


def cf_account(token: str) -> str:
    acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if acct:
        return acct
    accounts = _cf("GET", "/accounts", token)
    if not accounts:
        raise UrlError("the token can see no Cloudflare account")
    return accounts[0]["id"]


def ensure_domain(hostname: str, worker: str, token: str, account: str) -> str:
    """Attach ``hostname`` to the Worker if it is not already. Returns
    'present' or 'attached'. Cloudflare creates the DNS record itself."""
    existing = _cf("GET", f"/accounts/{account}/workers/domains?hostname={urllib.parse.quote(hostname)}",
                   token) or []
    for d in existing:
        if d.get("hostname") == hostname and d.get("service") == worker:
            return "present"
    _cf("PUT", f"/accounts/{account}/workers/domains", token,
        {"environment": "production", "hostname": hostname, "service": worker})
    return "attached"


def ship_worker(stage: Path, worker: str, host: str | None, *, message: str = "",
                wrangler: str = "wrangler@4.86.0", compatibility_date: str = "2026-08-15",
                log=print) -> dict:
    """Ship a directory as a Cloudflare Worker with static assets and, when
    ``host`` is given, make sure that hostname is attached to it.

    Shared by `hee url deploy` (a built redirect tree) and `hee deploy
    worker` (any static directory, e.g. get.hee.tools). One wrangler
    invocation, one domain-attach path, not two that drift. Needs Node >=
    20 and a token from cf_token(); HEE_CRED_PASS is scrubbed from the
    child's environment so wrangler never sees the sealed value under the
    generic name."""
    if shutil.which("npx") is None:
        raise UrlError("npx not found; wrangler needs Node >= 20")
    node = subprocess.run(["node", "-v"], capture_output=True, text=True, check=False).stdout.strip()
    major = int(re.sub(r"\D", " ", node).split()[0] or 0) if node else 0
    if major < 20:
        raise UrlError(f"Node >= 20 required for wrangler, found {node or 'none'}")
    token = cf_token()
    account = cf_account(token)
    env = dict(os.environ, CLOUDFLARE_API_TOKEN=token, CLOUDFLARE_ACCOUNT_ID=account)
    env.pop("HEE_CRED_PASS", None)
    cmd = ["npx", "--yes", wrangler, "deploy", "--name", worker, "--assets", ".",
           f"--compatibility-date={compatibility_date}"]
    if message:
        cmd += ["--message", message]
    r = subprocess.run(cmd, cwd=stage, env=env, capture_output=True, text=True, check=False)
    wanted = [ln for ln in (r.stdout + r.stderr).splitlines()
              if re.search(r"Success|rror|requires|Deployed|Uploaded", ln)]
    for ln in wanted:
        log(f"  wrangler: {ln.strip()}")
    if r.returncode != 0:
        raise UrlError(f"wrangler deploy exited {r.returncode}")
    out = {"deployed": True, "worker": worker}
    if host:
        how = ensure_domain(host, worker, token, account)
        log(f"custom domain {host}: {how}")
        out["domain"] = how
    return out


def deploy(cfg: dict, *, dry_run: bool = False, message: str = "", log=print) -> dict:
    """Build the tree and ship it as a Worker with static assets, then make
    sure the base hostname is attached to that Worker."""
    records = load_all(cfg)
    host = urllib.parse.urlsplit(str(cfg["base"])).netloc
    stage = Path(tempfile.mkdtemp(prefix="hee-url-"))
    try:
        slugs = build(cfg, stage, records)
        log(f"built {len(slugs)} link(s) into {stage} for {host} (worker {cfg['worker']})")
        if dry_run:
            log("dry run: not deploying")
            return {"slugs": slugs, "deployed": False}
        shipped = ship_worker(stage, cfg["worker"], host, message=message,
                              wrangler=cfg["wrangler"], compatibility_date=cfg["compatibility_date"],
                              log=log)
        return {"slugs": slugs, "deployed": True, "domain": shipped.get("domain")}
    finally:
        shutil.rmtree(stage, ignore_errors=True)
