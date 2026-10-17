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


def start(name: str, repo_dir: str, *, host: str, vmid, ref: str = "HEAD", runner=None, dry_run: bool = False) -> dict:
    """Ship the repo in and tag the baseline. Returns what was (or would be) done."""
    repo_name = os.path.basename(os.path.abspath(repo_dir.rstrip("/")))
    root = job_root(name, repo_name)
    tar = archive(repo_dir, ref)
    shell = (f"set -e; umask 022; mkdir -p {shlex.quote(root)} && cd {shlex.quote(root)} && tar -x && "
             f"printf '%s\\n' {shlex.quote(repo_name)} > {shlex.quote(f'{WORK}/{name}/.repo')} && "
             f"git init -q && git add -A && git {_git_id()} commit -q --allow-empty -m baseline && git tag -f baseline")
    cmd = pct_shell(host, vmid, shell) if not dry_run else ["(dry run)", "pct", "exec", str(vmid), "--", "su", "llm", "-c", shell]
    if not dry_run:
        run(cmd, stdin=tar, runner=runner)
    return {"name": name, "repo": repo_name, "ref": ref, "root": root, "bytes": len(tar), "shell": shell, "dry_run": dry_run}


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


def guard(name: str, args: dict, root: str) -> tuple[dict, str | None]:
    """Keep every path inside the job root; cd the shell there. Returns (args, refusal)."""
    args = dict(args or {})
    root = posixpath.normpath(root)
    for k in _PATH_KEYS:
        if k in args and isinstance(args[k], str):
            p = args[k]
            full = posixpath.normpath(p if p.startswith("/") else posixpath.join(root, p))
            if full != root and not full.startswith(root + "/"):
                return args, f"refused: {name} path {p!r} is outside the job root {root}"
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


def ask(endpoint: str, root: str, prompt: str, *, allow: tuple[str, ...] = READ_TOOLS, max_steps: int = 8,
        max_tokens: int = 512, model: str = "default", timeout: float = 300, log=None) -> dict:
    """Run the tool loop until the model answers in text or the step budget ends."""
    tools = fetch_tools(endpoint, allow)
    system = (f"You are working inside the directory {root}, a checkout of a git repository. "
              f"Use the tools to look at files there; paths are relative to it. Do not guess file contents: read them. "
              f"Answer concisely when you have what you need.")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    steps: list[dict] = []
    for _ in range(max_steps):
        choice = chat(endpoint, messages, tools, model=model, max_tokens=max_tokens, timeout=timeout)
        msg = choice.get("message") or {}
        calls = msg.get("tool_calls") or []
        if not calls:
            return {"answer": msg.get("content") or "", "steps": steps, "messages": messages, "stopped": False}
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for c in calls:
            fn = (c.get("function") or {})
            name = fn.get("name") or ""
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                args = {}
            if name not in allow:
                result = f"refused: tool {name!r} is not allowed for this job"
            else:
                args, refusal = guard(name, args, root)
                result = refusal or call_tool(endpoint, name, args, timeout=timeout)
            steps.append({"tool": name, "args": args, "result": result})
            if log:
                log(f"{name} {json.dumps(args)[:160]} -> {result[:120]!r}")
            messages.append({"role": "tool", "tool_call_id": c.get("id") or "", "content": result})
    return {"answer": f"(stopped after {max_steps} tool steps without a final answer)", "steps": steps,
            "messages": messages, "stopped": True}
