"""hee_llm -- give a local model work, not access: a checkout in, a patch out.

Operator, 2026-10-16: "where should it keep its git worktrees? how do we
allow it access?" The model server (llama-server with ``--agent``) runs its
built-in tools inside its own container as its own user. So a job is:

1. ``start``   -- ``git archive`` of a repo at a ref, shipped over ``pct exec``
                  into ``WORK/<job>/<repo>``, with a local ``baseline`` tag;
2. ``ask``     -- the tool loop over the OpenAI-compatible API: the model is
                  given the server's tool definitions (read-only by default),
                  every call is path-guarded to the job's root, executed by
                  ``POST /tools`` on the server, and fed back until the model
                  answers in text or the step budget runs out;
3. ``collect`` -- ``git format-patch baseline`` out of the container into a
                  local directory, for ``git am`` on a branch under the
                  dispatcher's own identity.

No repository credential ever enters the container; nothing it produces
reaches a repo unreviewed. The transport is ``ssh root@HOST pct exec VMID``,
the same path ``hee pve deploy`` uses; it is injectable here so every step
tests without a node.

Nothing fleet-specific lives here: host, vmid and endpoint come from flags or
``HEE_LLM_HOST`` / ``HEE_LLM_VMID`` / ``HEE_LLM_ENDPOINT``.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import shlex
import subprocess
import urllib.error
import urllib.parse
import urllib.request

__all__ = [
    "OUT",
    "READ_TOOLS",
    "SHELL_TOOLS",
    "WORK",
    "WRITE_TOOLS",
    "LlmError",
    "allowed_tools",
    "archive",
    "ask",
    "call_tool",
    "chat",
    "collect",
    "fetch_tools",
    "guard",
    "job_root",
    "list_jobs",
    "pct_shell",
    "remove",
    "repo_name_of",
    "run",
    "start",
    "valid_name",
]

WORK = "/var/lib/llm/work"
OUT = "/var/lib/llm/out"
READ_TOOLS = ("read_file", "file_glob_search", "grep_search", "get_info")
WRITE_TOOLS = ("write_file", "edit_file")
SHELL_TOOLS = ("exec_shell_command",)
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_PATH_KEYS = ("path",)


class LlmError(Exception):
    """A refusal: bad job name, no node, the server said no, a guard tripped."""


def valid_name(name: str) -> str:
    if not _NAME.match(name or ""):
        raise LlmError(f"job name {name!r}: letters, digits, . _ - only, up to 64, not starting with a dot")
    return name


def job_root(name: str, repo_name: str) -> str:
    return f"{WORK}/{valid_name(name)}/{valid_name(repo_name)}"


# --------------------------------------------------------------------------
# transport: ssh root@HOST pct exec VMID -- su llm -c SHELL
# --------------------------------------------------------------------------

def pct_shell(host: str, vmid, shell: str, user: str = "llm") -> list[str]:
    """The exact argv that runs SHELL inside the container as USER.

    ssh joins everything after the host with spaces and hands it to the
    node's shell, so the remote command is ONE string with SHELL quoted for
    that shell; otherwise `su -c` receives only its first word (measured
    2026-10-16: "Try 'su --help'", then the node looking for `git`).
    """
    if not host:
        raise LlmError("no node: --host HOST or HEE_LLM_HOST")
    if not str(vmid or "").isdigit():
        raise LlmError("no container: --vmid N or HEE_LLM_VMID")
    remote = f"pct exec {int(vmid)} -- su -s /bin/sh {shlex.quote(user)} -c {shlex.quote(shell)}"
    return ["ssh", "-o", "BatchMode=yes", f"root@{host}", remote]


def remote_shell(argv: list[str]) -> str:
    """The SHELL a pct_shell argv carries, unquoted again (for logs and tests)."""
    return shlex.split(argv[-1])[-1]


def run(cmd: list[str], stdin: bytes | None = None, runner=None) -> subprocess.CompletedProcess:
    """Run argv; ``runner`` replaces subprocess.run in tests."""
    fn = runner or (lambda c, inp: subprocess.run(c, input=inp, capture_output=True, check=False))
    r = fn(cmd, stdin)
    if r.returncode != 0:
        err = (r.stderr or b"").decode("utf-8", "replace").strip() if isinstance(r.stderr, bytes) else str(r.stderr or "")
        raise LlmError(f"{' '.join(cmd[:4])}... exited {r.returncode}: {err[-400:]}")
    return r


def archive(repo_dir: str, ref: str = "HEAD") -> bytes:
    """``git archive`` of the repo at ref: tracked files only, no .git, no secrets outside the tree."""
    r = subprocess.run(["git", "-C", repo_dir, "archive", "--format=tar", ref], capture_output=True, check=False)
    if r.returncode != 0:
        raise LlmError(f"git archive {ref} in {repo_dir}: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout


def _git_id() -> str:
    return "-c user.name=hee-llm -c user.email=hee-llm@localhost"


def start(name: str, repo_dir: str | None = None, *, host: str, vmid, ref: str = "HEAD", runner=None,
          dry_run: bool = False, from_path: str | None = None) -> dict:
    """Ship the repo in and tag the baseline. Returns what was (or would be) done.

    Two sources: ``repo_dir`` (a local checkout, ``git archive`` at ``ref``,
    shipped on stdin) or ``from_path`` (a path INSIDE the container, such as a
    read-only mirror on a share: copied, history kept, nothing crosses the
    wire). Exactly one of them.
    """
    if bool(repo_dir) == bool(from_path):
        raise LlmError("start takes exactly one source: --repo DIR (local) or --from PATH (inside the container)")
    marker = shlex.quote(f"{WORK}/{name}/.repo")
    if from_path:
        if not from_path.startswith("/"):
            raise LlmError("--from PATH is a path inside the container and must be absolute")
        repo_name = os.path.basename(from_path.rstrip("/"))
        root = job_root(name, repo_name)
        # A COPY, not a clone: the mirror is another user's (root's) tree and
        # git >= 2.35 refuses to read it as a repository ("dubious ownership")
        # in every form tried on 2026-10-17 (-c safe.directory for the work
        # tree, for its .git, via GIT_CONFIG_*, "*"), because the local
        # upload-pack side re-checks. The copy is the job user's own, history
        # included (144 MB for all 21 repositories, so a few MB each).
        shell = (f"set -e; umask 022; mkdir -p {shlex.quote(f'{WORK}/{name}')} && "
                 f"cp -r {shlex.quote(from_path)} {shlex.quote(root)} && "
                 f"cd {shlex.quote(root)} && git tag -f baseline && "
                 f"printf '%s\\n' {shlex.quote(repo_name)} > {marker}")
        tar = b""
    else:
        repo_name = os.path.basename(os.path.abspath(repo_dir.rstrip("/")))
        root = job_root(name, repo_name)
        tar = archive(repo_dir, ref)
        shell = (f"set -e; umask 022; mkdir -p {shlex.quote(root)} && cd {shlex.quote(root)} && tar -x && "
                 f"git init -q && git add -A && git {_git_id()} commit -q --allow-empty -m baseline && git tag -f baseline && "
                 f"printf '%s\\n' {shlex.quote(repo_name)} > {marker}")
    if not dry_run:
        run(pct_shell(host, vmid, shell), stdin=tar or None, runner=runner)
    return {"name": name, "repo": repo_name, "ref": ref if not from_path else "HEAD of " + from_path, "root": root,
            "bytes": len(tar), "shell": shell, "dry_run": dry_run, "from": from_path}


def repo_name_of(name: str, *, host: str, vmid, runner=None) -> str:
    r = run(pct_shell(host, vmid, f"cat {shlex.quote(f'{WORK}/{valid_name(name)}/.repo')}"), runner=runner)
    out = (r.stdout or b"").decode("utf-8", "replace").strip() if isinstance(r.stdout, bytes) else str(r.stdout).strip()
    if not out:
        raise LlmError(f"job {name!r} has no .repo marker; was it started?")
    return valid_name(out)


def collect(name: str, out_dir: str, *, host: str, vmid, repo_name: str | None = None, runner=None) -> dict:
    """Commit whatever the model left uncommitted, then ``format-patch baseline`` into out_dir/NAME.patch."""
    repo_name = repo_name or repo_name_of(name, host=host, vmid=vmid, runner=runner)
    root = job_root(name, repo_name)
    shell = (f"set -e; cd {shlex.quote(root)} && git add -A && "
             f"(git diff --cached --quiet || git {_git_id()} commit -q -m {shlex.quote(f'hee llm job {name}')}) && "
             f"mkdir -p {shlex.quote(f'{OUT}/{name}')} && git format-patch baseline --stdout | tee {shlex.quote(f'{OUT}/{name}/{name}.patch')}")
    r = run(pct_shell(host, vmid, shell), runner=runner)
    patch = r.stdout if isinstance(r.stdout, bytes) else str(r.stdout).encode()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.patch")
    with open(path, "wb") as f:
        f.write(patch)
    commits = len(re.findall(rb"^From [0-9a-f]{40} ", patch, re.MULTILINE))
    return {"name": name, "repo": repo_name, "path": path, "bytes": len(patch), "commits": commits}


def list_jobs(*, host: str, vmid, runner=None) -> list[str]:
    r = run(pct_shell(host, vmid, f"ls -1 {WORK} 2>/dev/null || true"), runner=runner)
    out = r.stdout.decode("utf-8", "replace") if isinstance(r.stdout, bytes) else str(r.stdout)
    return [ln.strip() for ln in out.splitlines() if ln.strip() and not ln.startswith(".")]


def remove(name: str, *, host: str, vmid, runner=None) -> None:
    valid_name(name)
    run(pct_shell(host, vmid, f"rm -rf {shlex.quote(f'{WORK}/{name}')} {shlex.quote(f'{OUT}/{name}')}"), runner=runner)


# --------------------------------------------------------------------------
# dispatcher-side tools: run by hee-llm itself, not by the server
# --------------------------------------------------------------------------
# The container has no egress policy of its own and no credentials; anything
# that reaches the internet runs on the dispatching host, which is the one
# with a user behind it. Two tools, both read-only, both clipped like the
# server's. The search backend is a URL template (HEE_LLM_SEARCH_URL, {q});
# the default is DuckDuckGo's HTML endpoint, which needs no key.

WEB_TOOLS = ("web_search", "fetch_url")
_TAG = re.compile(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", re.DOTALL | re.IGNORECASE)
_WS = re.compile(r"[ \t\r\f\v]+")
_NL = re.compile(r"\n{3,}")


def html_text(html: str) -> str:
    """Tags and scripts out, entities decoded, whitespace folded: the page as text."""
    import html as _html
    text = _TAG.sub(" ", html)
    text = _html.unescape(text)
    text = _WS.sub(" ", text)
    return _NL.sub("\n\n", "\n".join(ln.strip() for ln in text.splitlines())).strip()


def _get(url: str, timeout: float) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "hee-llm/1 (+https://tcos.us)", "Accept": "text/html,application/json;q=0.9,*/*;q=0.5"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = r.headers.get("content-type", "")
            return r.read(2_000_000).decode("utf-8", "replace"), ctype
    except urllib.error.HTTPError as e:
        raise LlmError(f"HTTP {e.code} {e.reason} for {url}") from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise LlmError(f"{url}: {getattr(e, 'reason', e)}") from e


_DDG_RESULT = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?(?:<a[^>]+class="result__snippet"[^>]*>(.*?)</a>)?', re.DOTALL)


def web_search(args: dict, timeout: float = 30) -> str:
    q = str(args.get("query") or "").strip()
    if not q:
        return "tool error: query is required"
    limit = max(1, min(int(args.get("limit") or 5), 10))
    template = os.environ.get("HEE_LLM_SEARCH_URL") or "https://html.duckduckgo.com/html/?q={q}"
    url = template.replace("{q}", urllib.parse.quote_plus(q))
    try:
        body, ctype = _get(url, timeout)
    except LlmError as e:
        return f"tool error: {e}"
    rows = []
    if "json" in ctype:
        try:
            data = json.loads(body)
            for r in (data.get("results") or data if isinstance(data, dict) else data)[:limit]:
                rows.append(f"- {r.get('title','')}\n  {r.get('url','')}\n  {r.get('content') or r.get('snippet') or ''}".rstrip())
        except (ValueError, AttributeError, TypeError):
            return "tool error: search backend returned unreadable JSON"
    else:
        for m in _DDG_RESULT.finditer(body):
            href, title, snippet = m.group(1), html_text(m.group(2)), html_text(m.group(3) or "")
            # DuckDuckGo wraps targets as //duckduckgo.com/l/?uddg=<url>; unwrap to the real address
            mm = re.search(r"[?&]uddg=([^&]+)", href)
            if mm:
                href = urllib.parse.unquote(mm.group(1))
            rows.append(f"- {title}\n  {href}\n  {snippet}".rstrip())
            if len(rows) >= limit:
                break
    if not rows:
        return f"no results for {q!r} (backend: {template.split('?')[0]})"
    return f"results for {q!r}:\n" + "\n".join(rows)


def fetch_url(args: dict, timeout: float = 30) -> str:
    url = str(args.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return "tool error: url must start with http:// or https://"
    try:
        body, ctype = _get(url, timeout)
    except LlmError as e:
        return f"tool error: {e}"
    text = body if ("json" in ctype or "text/plain" in ctype) else html_text(body)
    return f"{url} ({ctype.split(';')[0] or 'unknown type'}):\n{text}"


LOCAL_TOOLS = {
    "web_search": {
        "run": web_search,
        "definition": {"type": "function", "function": {
            "name": "web_search",
            "description": "Search the web. Returns up to `limit` results as title, URL and snippet. Use fetch_url to read one.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "What to search for"},
                "limit": {"type": "integer", "description": "How many results, 1-10 (default 5)"}},
                "required": ["query"]}}},
    },
    "fetch_url": {
        "run": fetch_url,
        "definition": {"type": "function", "function": {
            "name": "fetch_url",
            "description": "Fetch a web page or API URL and return its text (HTML is reduced to text). Long pages are cut; ask for what you need.",
            "parameters": {"type": "object", "properties": {
                "url": {"type": "string", "description": "An http or https URL"}},
                "required": ["url"]}}},
    },
}

# --------------------------------------------------------------------------
# the tool loop over the API
# --------------------------------------------------------------------------

def _http(url: str, body: dict | None = None, timeout: float = 300) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data, {"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except ValueError:
            raise LlmError(f"{url}: HTTP {e.code} {e.reason}") from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise LlmError(f"{url}: {getattr(e, 'reason', e)}") from e


def allowed_tools(allow_write: bool = False, allow_shell: bool = False) -> tuple[str, ...]:
    names = READ_TOOLS + (WRITE_TOOLS if allow_write else ()) + (SHELL_TOOLS if allow_shell else ())
    return names


def fetch_tools(endpoint: str, allow: tuple[str, ...], timeout: float = 30) -> list[dict]:
    """The server's tool definitions (``GET /tools``), filtered to the allowed names."""
    rows = _http(endpoint.rstrip("/") + "/tools", timeout=timeout)
    if isinstance(rows, dict) and rows.get("error"):
        raise LlmError(f"{endpoint}/tools: {rows['error']}")
    if not isinstance(rows, list):
        raise LlmError(f"{endpoint}/tools: the server does not expose tools (is it started with --agent?)")
    return [r["definition"] for r in rows if isinstance(r, dict) and r.get("tool") in allow and r.get("definition")]


def _under(full: str, base: str) -> bool:
    base = posixpath.normpath(base)
    return full == base or full.startswith(base + "/")


def guard(name: str, args: dict, root: str, read_roots: tuple[str, ...] = ()) -> tuple[dict, str | None]:
    """Keep every path inside the job root; cd the shell there. Returns (args, refusal).

    ``read_roots`` are extra trees a READ-ONLY tool may look at (a mirror of
    other repositories on a share, for instance); a write tool is still held
    to the job root, whatever the roots say.
    """
    args = dict(args or {})
    root = posixpath.normpath(root)
    for k in _PATH_KEYS:
        if k in args and isinstance(args[k], str):
            p = args[k]
            full = posixpath.normpath(p if p.startswith("/") else posixpath.join(root, p))
            if not _under(full, root):
                readable = name not in WRITE_TOOLS and any(_under(full, r) for r in read_roots)
                if not readable:
                    where = f"the job root {root}" if (name in WRITE_TOOLS or not read_roots) else f"{root} and the read-only roots {', '.join(read_roots)}"
                    return args, f"refused: {name} path {p!r} is outside {where}"
            args[k] = full
    if name == "exec_shell_command":
        cmd = str(args.get("command", ""))
        args["command"] = f"cd {shlex.quote(root)} && ({cmd})"
    return args, None


def call_tool(endpoint: str, name: str, args: dict, timeout: float = 120) -> str:
    """``POST /tools`` as the server expects it: ``{"tool": name, "params": {...}}``."""
    res = _http(endpoint.rstrip("/") + "/tools", {"tool": name, "params": args}, timeout=timeout)
    if isinstance(res, dict):
        if "plain_text_response" in res:
            return str(res["plain_text_response"])
        if res.get("error") or res.get("message"):
            err = res.get("error") or res
            return f"tool error: {err.get('message') if isinstance(err, dict) else err}"
    return json.dumps(res)


def chat(endpoint: str, messages: list[dict], tools: list[dict], *, model: str = "default",
         max_tokens: int = 512, timeout: float = 300) -> dict:
    body = {"model": model, "temperature": 0, "max_tokens": max_tokens, "messages": messages}
    if tools:
        body["tools"] = tools
    res = _http(endpoint.rstrip("/") + "/v1/chat/completions", body, timeout=timeout)
    if isinstance(res, dict) and res.get("error"):
        raise LlmError(f"chat: {res['error']}")
    try:
        return res["choices"][0]
    except (KeyError, IndexError, TypeError) as e:
        raise LlmError("chat: no choices[0] in the reply") from e


MAX_RESULT_CHARS = 3000   # a tool result longer than this is cut: the whole conversation must fit the server's context
CONTEXT_TOKENS = 8192     # the server's context; llm-1 runs -c 8192 (fleet-ops pve/llm/llm.environment)
CHARS_PER_TOKEN = 3.2     # a safe (low) estimate for English, code and JSON; measured 8639 tokens for ~26 kB on 2026-10-17
COMPACT_TO = 300          # an older tool result is cut to this many chars when the budget is reached


def est_tokens(messages: list[dict], tools: list[dict] | None = None) -> int:
    """A deliberately high estimate of the prompt tokens a request would take."""
    chars = len(json.dumps(messages)) + (len(json.dumps(tools)) if tools else 0)
    return int(chars / CHARS_PER_TOKEN) + 64


def compact(messages: list[dict], budget: int, tools: list[dict] | None = None) -> int:
    """Cut the OLDEST tool results to COMPACT_TO chars until the estimate fits ``budget``.

    Returns how many results were compacted. The system prompt, the user's
    question and the assistant's tool calls are never touched; only what the
    tools returned earlier in this loop, which the model has already acted on.
    """
    n = 0
    for m in messages:
        if est_tokens(messages, tools) <= budget:
            break
        if m.get("role") == "tool" and len(m.get("content") or "") > COMPACT_TO:
            m["content"] = m["content"][:COMPACT_TO] + " [... earlier result compacted to fit the context]"
            n += 1
    return n


def clip(text: str, limit: int = MAX_RESULT_CHARS) -> str:
    """Cut a tool result to the budget and say so, so the model knows it saw a prefix."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[... {len(text) - limit} more characters not shown; read a narrower range]"


def ask(endpoint: str, root: str, prompt: str, *, allow: tuple[str, ...] = READ_TOOLS, max_steps: int = 8,
        max_tokens: int = 512, model: str = "default", timeout: float = 300, log=None,
        read_roots: tuple[str, ...] = (), max_result_chars: int = MAX_RESULT_CHARS,
        context: int = CONTEXT_TOKENS, web: bool = False) -> dict:
    """Run the tool loop until the model answers in text or the step budget ends.

    Every tool result is clipped to ``max_result_chars`` before it goes back
    to the model: measured 2026-10-17, one whole README as a result pushed an
    8192-token server past "Context size has been exceeded".
    """
    tools = fetch_tools(endpoint, allow)
    extra = (f" You may also READ, not write, under {', '.join(read_roots)} (other repositories, read-only)." if read_roots else "")
    if web:
        extra += " You may search the web with web_search and read a page with fetch_url; cite the URL for anything you take from it."
    system = (f"You are working inside the directory {root}, a checkout of a git repository. "
              f"Use the tools to look at files there; paths are relative to it. Do not guess file contents: read them.{extra} "
              f"Answer concisely when you have what you need.")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    if web:
        tools = tools + [LOCAL_TOOLS[n]["definition"] for n in WEB_TOOLS]
    steps: list[dict] = []
    budget = context - max_tokens - 256
    seen: dict[str, int] = {}
    for step in range(max_steps):
        compacted = compact(messages, budget, tools)
        if compacted and log:
            log(f"(compacted {compacted} earlier tool result(s) to fit {context} tokens)")
        choice = chat(endpoint, messages, tools, model=model, max_tokens=max_tokens, timeout=timeout)
        msg = choice.get("message") or {}
        calls = msg.get("tool_calls") or []
        if not calls:
            return {"answer": msg.get("content") or "", "steps": steps, "messages": messages, "stopped": False}
        # A small model will re-issue the same call, or walk past the end of a file, until the
        # step budget is gone (measured 2026-10-17: six reads of empty line ranges). The third
        # repeat of an identical call, or the last step, ends the tool phase: the tools are
        # taken away and the model is asked to answer from what it has read, saying what it
        # could not.
        key = json.dumps([[(c.get("function") or {}).get("name"), (c.get("function") or {}).get("arguments")] for c in calls])
        seen[key] = seen.get(key, 0) + 1
        if seen[key] >= 3 or step == max_steps - 1:
            messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
            for c in calls:
                messages.append({"role": "tool", "tool_call_id": c.get("id") or "",
                                 "content": "not executed: the tool phase is over. Answer now from what you have already read, "
                                            "and say plainly what you could not read or did not find."})
            final = chat(endpoint, messages, [], model=model, max_tokens=max_tokens, timeout=timeout)
            answer = (final.get("message") or {}).get("content") or ""
            why = "a call repeated three times" if seen[key] >= 3 else f"the {max_steps}-step budget"
            if log:
                log(f"(tool phase ended by {why}; asked for a final answer without tools)")
            return {"answer": answer, "steps": steps, "messages": messages, "stopped": not answer.strip(), "ended_by": why}
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for c in calls:
            fn = (c.get("function") or {})
            name = fn.get("name") or ""
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                args = {}
            if web and name in WEB_TOOLS:
                result = clip(LOCAL_TOOLS[name]["run"](args, timeout=min(timeout, 60)), max_result_chars)
            elif name not in allow:
                result = f"refused: tool {name!r} is not allowed for this job"
            else:
                args, refusal = guard(name, args, root, read_roots)
                result = refusal or clip(call_tool(endpoint, name, args, timeout=timeout), max_result_chars)
            steps.append({"tool": name, "args": args, "result": result})
            if log:
                log(f"{name} {json.dumps(args)[:160]} -> {result[:120]!r}")
            messages.append({"role": "tool", "tool_call_id": c.get("id") or "", "content": result})
    return {"answer": "(no answer)", "steps": steps, "messages": messages, "stopped": True}
