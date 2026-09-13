"""hee_ghapp -- GitHub App installation tokens: one hour, narrowed per use.

fleet-ops#387 footgun 3, as the agent roster records it: "no agent holds a
long-lived token. The factory mints a GitHub App installation token per job,
one hour, scoped to that agent's repos and permissions". A personal access
token of either kind is the wrong tool for that -- GitHub: both kinds "are
tied to the user who generated them" -- so an org's automation acts through
an App the org owns:

  1. the App's private key signs a JWT (RS256, iss = the App's client id,
     at most ten minutes of life);
  2. the JWT finds the org's installation and buys an installation token
     (one hour), naming only the repositories and permissions one grant
     allows;
  3. the token is revoked as soon as the work it was minted for is over.

The registry (fleet-ops hee/registries/github-apps.registry.v1.yaml) holds
everything that is not secret: the org, each App's client id, its permission
ceiling, the keys its private key is sealed to, and one grant per identity.
The private key itself is a hee cred credential; nothing in this module
writes it anywhere, and no function returns it.
"""
import base64
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = os.environ.get("HEE_GITHUB_API", "https://api.github.com")
API_VERSION = "2022-11-28"
LEVELS = {"read": 1, "write": 2, "admin": 3}
MAX_REPOS = 500          # GitHub: a token may name at most 500 repositories
TOKEN_LIFETIME_S = 3600  # GitHub: installation tokens expire after one hour
DEFAULT_REGISTRY = os.path.expanduser("~/git/fleet-ops/hee/registries/github-apps.registry.v1.yaml")
REGISTRY_ENV = "HEE_GITHUB_APPS"
# GitHub hands out PKCS#1 PEM files; PKCS#8 is what a converted key looks like.
KEY_HEADERS = ("-----BEGIN RSA PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----")


class GitHubAppError(Exception):
    """Anything that stops a token from being minted or trusted. The message
    never carries a key or a token."""


# ---- the JWT -----------------------------------------------------------------

def _b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def app_jwt(pem, client_id, now=None):
    """A JWT for the App. GitHub: iat "60 seconds in the past" for clock
    drift, exp "no more than 10 minutes into the future", iss the client id
    ("recommended"), signed RS256."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
    except ImportError:
        raise GitHubAppError("minting a GitHub App token needs python3-cryptography") from None
    try:
        key = serialization.load_pem_private_key(pem.encode(), password=None)
    except (ValueError, TypeError):
        raise GitHubAppError("the sealed App key is not a readable, unencrypted PEM private key") from None
    if not isinstance(key, rsa.RSAPrivateKey):
        raise GitHubAppError("the sealed App key is not an RSA key -- GitHub App keys are RSA")
    now = int(time.time() if now is None else now)
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {"iat": now - 60, "exp": now + 540, "iss": str(client_id)}
    signing_input = (_b64url(json.dumps(header, separators=(",", ":")).encode()) + "."
                     + _b64url(json.dumps(claims, separators=(",", ":")).encode()))
    sig = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    return signing_input + "." + _b64url(sig)


# ---- the API -----------------------------------------------------------------

def call(method, path, bearer, body=None, api=None):
    """One REST call. Returns (status, parsed JSON or None). An HTTP error
    becomes GitHubAppError with GitHub's own message, which never echoes the
    credential that was sent."""
    api = (api or API).rstrip("/")
    url = path if path.startswith("http") else api + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": API_VERSION,
               "User-Agent": "hee-ghapp", "Authorization": f"Bearer {bearer}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        detail = e.read()[:300].decode("utf-8", "replace").strip()
        raise GitHubAppError(f"{method} {urllib.parse.urlsplit(url).path}: HTTP {e.code} {detail}") from None
    except urllib.error.URLError as e:
        raise GitHubAppError(f"{method} {url}: {e.reason}") from None


def installation(jwt, org, api=None):
    """The App's installation on ORG: id, permissions, repository_selection."""
    _, inst = call("GET", f"/orgs/{urllib.parse.quote(org)}/installation", jwt, api=api)
    return inst


def revoke(token, api=None):
    """DELETE /installation/token: the token stops working now, not in an
    hour. Returns True when GitHub confirmed it."""
    try:
        status, _ = call("DELETE", "/installation/token", token, api=api)
    except GitHubAppError:
        return False
    return status == 204


def _repositories(token, api=None):
    names, page = [], 1
    while True:
        _, doc = call("GET", f"/installation/repositories?per_page=100&page={page}", token, api=api)
        batch = [r["name"] for r in (doc or {}).get("repositories") or []]
        names += batch
        if len(batch) < 100 or len(names) >= int((doc or {}).get("total_count") or 0):
            return names
        page += 1


def check_permissions(requested, ceiling):
    """A grant may ask for a permission only if the App's ceiling holds it at
    the same level or higher. Raises, naming every excess at once."""
    bad = []
    for k, v in sorted(requested.items()):
        if v not in LEVELS:
            bad.append(f"{k}={v} (a level is read, write or admin)")
        elif k not in ceiling:
            bad.append(f"{k}={v} (not in the App's ceiling)")
        elif LEVELS[v] > LEVELS.get(ceiling[k], 0):
            bad.append(f"{k}={v} (the App's ceiling is {ceiling[k]})")
    if bad:
        raise GitHubAppError("grant asks for more than the App holds: " + "; ".join(bad))


def mint(pem, client_id, org, permissions, repos, api=None, now=None):
    """One installation token for one use.

    repos is either a list of repository names, or a regular expression
    (str) that must fullmatch a name; a regex is resolved against what the
    installation can actually see, through a probe token that can read
    metadata only and is revoked straight after.

    Returns {token, expires_at, installation_id, repositories, permissions}.
    GitHub's answer is checked against the request: a token whose
    permissions differ from what was asked is revoked and refused, never
    handed on."""
    jwt = app_jwt(pem, client_id, now)
    iid = installation(jwt, org, api)["id"]
    if isinstance(repos, str):
        try:
            rx = re.compile(repos)
        except re.error as e:
            raise GitHubAppError(f"repos pattern {repos!r} is not a regular expression: {e}") from None
        _, probe = call("POST", f"/app/installations/{iid}/access_tokens", jwt,
                        {"permissions": {"metadata": "read"}}, api)
        try:
            visible = _repositories(probe["token"], api)
        finally:
            revoke(probe["token"], api)
        chosen = sorted(n for n in visible if rx.fullmatch(n))
        if not chosen:
            raise GitHubAppError(f"repos pattern {repos!r} matches none of the {len(visible)} repositories "
                                 f"the installation on {org} can see")
    else:
        chosen = sorted(set(repos))
    if not chosen:
        raise GitHubAppError("a token must name at least one repository")
    if len(chosen) > MAX_REPOS:
        raise GitHubAppError(f"{len(chosen)} repositories; GitHub allows {MAX_REPOS} per token")
    _, tok = call("POST", f"/app/installations/{iid}/access_tokens", jwt,
                  {"repositories": chosen, "permissions": permissions}, api)
    granted = tok.get("permissions") or {}
    got = sorted(r["name"] for r in tok.get("repositories") or [])
    if granted != permissions or got != chosen:
        revoke(tok["token"], api)
        raise GitHubAppError(f"GitHub granted {granted} on {len(got)} repositories; asked for {permissions} "
                             f"on {len(chosen)} -- token revoked, not used")
    return {"token": tok["token"], "expires_at": tok.get("expires_at"), "installation_id": iid,
            "repositories": chosen, "permissions": granted}


# ---- the registry ------------------------------------------------------------

def registry_path(path=None):
    return path or os.environ.get(REGISTRY_ENV) or DEFAULT_REGISTRY


def load_registry(path=None):
    """(spec, resolved path). The registry is a hee/v1 Registry object."""
    try:
        import yaml
    except ImportError:
        raise GitHubAppError("reading the GitHub App registry needs pyyaml") from None
    path = registry_path(path)
    try:
        with open(path, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}
    except OSError as e:
        raise GitHubAppError(f"GitHub App registry {path}: {e.strerror} -- set {REGISTRY_ENV} or pass the path") from None
    spec = doc.get("spec") or {}
    if not spec.get("org") or not isinstance(spec.get("apps"), dict):
        raise GitHubAppError(f"{path}: spec needs org and apps")
    return spec, str(Path(path).resolve())


def store_dir(path):
    """The hee cred store beside a registry: <repo>/.hee/secrets for
    <repo>/hee/registries/<file>. So a sealed App key and the registry that
    names it travel in the same repository, and a command works from any
    directory."""
    return Path(path).resolve().parents[2] / ".hee" / "secrets"


def app_for_cred(spec, account):
    """(name, app) for the App whose private key is hee cred ACCOUNT."""
    for name, app in spec["apps"].items():
        if isinstance(app, dict) and app.get("cred") == account:
            return name, app
    known = ", ".join(sorted(a.get("cred", "?") for a in spec["apps"].values() if isinstance(a, dict)))
    raise GitHubAppError(f"no App in the registry is sealed as {account!r} (known: {known or 'none'})")


def resolve_grant(app, grant, registry, roster=None):
    """(permissions, repos) for one grant. permissions always carries
    metadata=read, which GitHub grants every token anyway; repos is a regex
    or a list. repos: agent-roster reads the ratified agent roster's
    scope.repos for the grant's name, so an agent's repositories have one
    source, not two."""
    g = (app.get("grants") or {}).get(grant)
    if not isinstance(g, dict):
        raise GitHubAppError(f"the App has no grant {grant!r} (grants: {', '.join(sorted(app.get('grants') or {})) or 'none'})")
    perms = {str(k): str(v) for k, v in (g.get("permissions") or {}).items()}
    perms.setdefault("metadata", "read")
    check_permissions(perms, {str(k): str(v) for k, v in (app.get("permissions") or {}).items()})
    repos = g.get("repos")
    if repos == "agent-roster":
        import yaml
        roster = roster or str(Path(registry).with_name("agent-roster.registry.v1.yaml"))
        try:
            with open(roster, encoding="utf-8") as fh:
                agents = ((yaml.safe_load(fh) or {}).get("spec") or {}).get("agents") or {}
        except OSError as e:
            raise GitHubAppError(f"grant {grant!r} takes its repos from the agent roster, and {roster}: {e.strerror}") from None
        repos = ((agents.get(grant) or {}).get("scope") or {}).get("repos")
        if not repos:
            raise GitHubAppError(f"grant {grant!r}: the agent roster has no scope.repos for {grant!r}")
    if not (isinstance(repos, str) and repos) and not (isinstance(repos, list) and repos):
        raise GitHubAppError(f"grant {grant!r}: repos must be a regex, a list of names, or agent-roster")
    return perms, repos


def registration_url(org, app):
    """GitHub's register-by-URL form for an org App, pre-filled from the
    registry: name, homepage, description, private, no webhook, and every
    permission in the ceiling. GitHub always grants metadata read, so it is
    not a parameter."""
    reg = app.get("registration") or {}
    q = [("name", reg.get("name", "")), ("url", reg.get("url", "")), ("description", reg.get("description", "")),
         ("public", "false"), ("webhook_active", "false")]
    q += sorted((str(k), str(v)) for k, v in (app.get("permissions") or {}).items() if k != "metadata")
    return (f"https://github.com/organizations/{urllib.parse.quote(org)}/settings/apps/new?"
            + urllib.parse.urlencode(q))


def compare_installation(inst, ceiling):
    """[(level, message)] comparing what the org actually approved with the
    registry's ceiling. More than the ceiling is CRITICAL (the registry no
    longer bounds the App); less is WARNING (a grant that needs it will be
    refused by GitHub until an owner approves the change)."""
    out = []
    have = {str(k): str(v) for k, v in (inst.get("permissions") or {}).items()}
    want = {str(k): str(v) for k, v in ceiling.items()}
    for k in sorted(set(have) | set(want)):
        h, w = have.get(k), want.get(k)
        if h == w:
            continue
        if w is None or LEVELS.get(h, 0) > LEVELS.get(w, 0):
            out.append(("CRITICAL", f"installation holds {k}={h}; the registry's ceiling is {w or 'nothing'}"))
        else:
            out.append(("WARNING", f"installation holds {k}={h or 'nothing'}; the registry's ceiling is {w} -- "
                                   "an owner has to approve the App's permission change"))
    if inst.get("suspended_at"):
        out.append(("CRITICAL", f"installation suspended at {inst['suspended_at']}"))
    return out
