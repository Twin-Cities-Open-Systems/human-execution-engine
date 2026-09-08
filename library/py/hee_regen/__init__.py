"""hee_regen -- the regeneration pass behind ``hee repo-refresh regen``.

The org had at least five generated artifacts and no scheduler. Measured
2026-09-08: no crontab entry, no workflow and no systemd timer referenced
any of them; ``fleet-ops/pve/network-map.md`` carried a written admission
that "regeneration is a habit, not a gate", and the copy of
``old-commits.html`` served by ct107 was two days and 31 branches behind
its own inputs. ``hee pve-health drift`` already DETECTED two of them.
Nothing acted on any of it.

This module is the acting half. It is a library, not a tool, per rule 15 --
``tooling/bin/hee-repo-refresh`` stays thin and this is where the logic
lives, testable and reusable.

The one real idea
-----------------
**A generator's exit code is its source-reachability answer.** Every hee
generator already speaks the Nagios vocabulary the whole org speaks:

    0  rendered              -> compare it
    3  source not reachable  -> UNKNOWN, never "unchanged"
    2  generator broke       -> CRITICAL

So this pass needs no per-generator special case to tell "the pve API is
down" apart from "the map is current". It reads the number the generator
already returns. That is the entire fail-closed mechanism, and it is why
adding an artifact here is a table row rather than a code path.

FAILS CLOSED, for the reason rule 16 names in blood: ``namespace-audit``
reported "OK -- no naming ambiguity found across 17 repo(s)" every day from
2026-08-31 while its token was empty and it had read none of them
(issue:423@fleet-ops). An artifact whose source could not be reached is
UNKNOWN here, is counted in the summary, and is named in the "not reached"
line -- it never becomes a shorter list of OKs.

NEVER COMMITS. Regenerating is not landing. This writes files; a human, or
a later step, opens the PR.
"""

from __future__ import annotations

import difflib
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hee_status import Status, render  # noqa: E402

__all__ = ["ARTIFACTS", "Artifact", "Result", "main", "run_pass"]

REPO_ROOT = Path(__file__).resolve().parents[3]
BIN = REPO_ROOT / "tooling" / "bin"

# Seconds any one generator may take before the pass reports it as
# unanswered rather than waiting on it. Same reasoning as
# hee-repo-refresh's HEE_GIT_TIMEOUT: one wedged host must not hang the
# whole run, and a hang must not be reported as a result.
TIMEOUT = int(os.environ.get("HEE_REGEN_TIMEOUT", "300"))

# Volatile stamps a renderer writes into its own output. Two renders of
# identical DATA differ only here, so they are normalized away before a
# published page is compared -- otherwise every run reports a change and
# the check is permanently red, which rule 16 measures the cost of.
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?")


@dataclass
class Artifact:
    """One generated artifact: where it lives, what makes it, what it needs.

    ``kind`` picks the strategy, and each is a real, different shape:

    block    the generator prints the artifact to stdout and it lives
             between ``<!-- marker:start -->`` / ``<!-- marker:end -->`` in
             a committed file whose surrounding prose is authored and must
             survive. Compared and spliced here.
    tool     the generator already implements dry-run-plus-``--write``
             itself (hee-gen-manpages, hee-gen-changelog). Delegated to,
             never reimplemented: a second copy of a renderer is the shape
             that produced three divergent TCOS taxonomies.
    publish  the artifact is not committed anywhere -- it is rendered and
             pushed to a host. Rendered and compared against what is
             actually published; NEVER deployed, because deploying is
             landing and this pass does not land.
    """

    repo: str
    label: str
    source: str                     # human name of what must be reachable
    kind: str                       # block | tool | publish
    cmd: list                       # render/dry-run command
    dest: str = ""                  # path relative to the repo
    marker: str = ""                # block kind only
    current_re: str = ""            # tool kind: stdout line meaning "already current"
    stale_re: str = ""              # tool kind: the tool's own line saying what would change
    write_args: list = field(default_factory=list)   # tool kind: what --write adds
    published_url: str = ""         # publish kind
    land: str = ""                  # the operator action that lands it


def _hee(*args):
    """A generator named the way `hee` names it, resolved later, per repo.

    Deliberately NOT an absolute path into this checkout. Measured on the
    first full run: with the path baked in, `regen all` ran THIS worktree's
    hee-gen-manpages and reported "4 changed" about man/tools -- while
    printing the name of the repo it had been asked about, which was clean.
    A generator that documents a repo has to be that repo's own.
    """
    return [f"hee-{args[0]}", *[str(a) for a in args[1:]]]


def _resolve(cmd, repo_dir: Path):
    """(argv, error). The `hee` router's own resolution order, reused.

    1. the repo being regenerated, if it ships the tool
    2. the repo this library lives in

    Same order as tooling/bin/hee, and for the same reason: the checkout you
    are pointed at wins over the checkout the tool happens to live in.
    """
    name = cmd[0]
    if "/" in name:                       # already repo-relative, e.g. bin/x.py
        cand = repo_dir / name
        return ([str(cand), *cmd[1:]], None) if cand.is_file() else (None, f"no generator at {cand}")
    for base in (repo_dir / "tooling" / "bin", BIN):
        cand = base / name
        if cand.is_file():
            return [str(cand), *cmd[1:]], None
    return None, f"{name} is not in {repo_dir}/tooling/bin or {BIN}"


ARTIFACTS = [
    Artifact(
        repo="fleet-ops", label="pve/addressing.md [pve-inventory]",
        source="pve API", kind="block",
        dest="pve/addressing.md", marker="pve-inventory",
        cmd=_hee("pve-health", "inventory"),
        land="commit fleet-ops/pve/addressing.md on a branch and open a PR",
    ),
    Artifact(
        repo="fleet-ops", label="pve/network-map.md [pve-map]",
        source="pve API + haproxy ct103", kind="block",
        dest="pve/network-map.md", marker="pve-map",
        cmd=_hee("pve-health", "map"),
        land="commit fleet-ops/pve/network-map.md on a branch and open a PR",
    ),
    Artifact(
        # The one artifact here whose source is a FILE, not a machine. It is
        # in the pass on purpose: a pass that only ever talks to the network
        # cannot show that it distinguishes "unreachable" from "unchanged".
        repo="fleet-ops", label="pve/network-map.md [pve-map-proposed]",
        source="agent-roster registry (local file)", kind="block",
        dest="pve/network-map.md", marker="pve-map-proposed",
        cmd=_hee("pve-health", "map", "--proposed"),
        land="commit fleet-ops/pve/network-map.md on a branch and open a PR",
    ),
    Artifact(
        repo="human-execution-engine", label="man/tools/",
        source="the tools' own --help (local)", kind="tool",
        dest="man/tools",
        cmd=_hee("gen-manpages"), write_args=["--write"],
        current_re=r"^\s*0 changed\s+0 new\s+0 removed\b",
        stale_re=r"^\s*\d+ changed\s+\d+ new\s+\d+ removed\b.*$",
        land="commit man/tools/ on a branch and open a PR (rule 17)",
    ),
    Artifact(
        repo="human-execution-engine", label="CHANGELOG.md",
        source="git log main (local)", kind="tool",
        dest="CHANGELOG.md",
        cmd=_hee("gen-changelog"), write_args=["--write"],
        current_re=r"^.*CHANGELOG\.md \[Unreleased\] is current\s*$",
        stale_re=r"^.*CHANGELOG\.md \[Unreleased\] would change.*$",
        land="commit CHANGELOG.md in a chore PR after a batch of merges (rule 18)",
    ),
    Artifact(
        repo=".github", label="view.lab old-commits.html",
        source="origin branches of every org repo + gh, then view.lab.tcos.us",
        kind="publish",
        cmd=["bin/render-old-commits.py"],
        published_url="https://view.lab.tcos.us/old-commits.html",
        land="make -C ~/git/.github lab-old-commits",
    ),
]


@dataclass
class Result:
    artifact: Artifact
    status: Status
    detail: str
    diff: list = field(default_factory=list)
    reached: bool = True            # was the artifact's source readable?


# ---------------------------------------------------------------- helpers


def _run(cmd, cwd, timeout=None):
    """(rc, stdout, stderr). rc 124 means it never answered, as in timeout(1).

    A command that did not finish is not a command that returned nothing --
    rule 2's silence-as-a-result, which cost hee-repo-refresh a whole release
    when 18 of 19 repos were reported "remote is empty".
    """
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                           timeout=timeout or TIMEOUT)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"did not answer within {timeout or TIMEOUT}s"
    except OSError as e:
        return 127, "", str(e)


# A status line the delegated generator already rendered: icon+label, or
# [WARN], or the bare word under HEE_STATUS_STYLE=plain. Stripped when that
# line is quoted INSIDE this pass's own status line, or the report reads
# "WARNING ...: WARNING ..." -- which it did on the first run.
_STATUS_PREFIX = re.compile(r"^\s*(?:\S{1,3}\s*)?(?:\[)?(OK|WARN|WARNING|CRIT|CRITICAL|UNKN|UNKNOWN)(?:\])?\s+")


def _classify_generator(rc, err, source):
    """Map a generator's own exit code onto this pass's verdict.

    Nagios all the way down: the generator already decided whether its
    source was reachable and said so in its exit code. Reading that number
    is what keeps this pass from guessing.
    """
    if rc == 0:
        return None
    lines = [x for x in err.strip().splitlines() if x.strip()]
    # The generator already rendered its own icon+label. Quoting it verbatim
    # inside this pass's status line prints the vocabulary twice.
    tail = f" -- {_STATUS_PREFIX.sub('', lines[-1].strip())}" if lines else ""
    if rc == 124:
        return Status.UNKNOWN, f"{source} did not answer within {TIMEOUT}s -- skipped, NOT unchanged"
    if rc == 3:
        return Status.UNKNOWN, f"{source} not reachable{tail} -- skipped, NOT unchanged"
    if rc == 127:
        return Status.CRITICAL, f"generator could not be run{tail}"
    return Status.CRITICAL, f"generator exited {rc}{tail}"


def _identity(repo_dir: Path):
    """Which REPO is this directory a checkout of?

    Not the directory name. A worktree of human-execution-engine is called
    ~/git/human-execution-engine.worktrees/kiosk-regen-pass, and matching the
    registry on the directory name reported "no repo in scope declares a
    generated artifact" for it -- a fail-open answer about a repo that
    declares five. The origin URL knows; the path does not.
    """
    rc, out, _ = _run(["git", "remote", "get-url", "origin"], repo_dir, timeout=15)
    if rc == 0 and out.strip():
        return re.sub(r"\.git$", "", out.strip().rstrip("/").rsplit("/", 1)[-1])
    return repo_dir.name


def _dirty(repo_dir):
    """Paths with uncommitted changes at the START of the pass.

    Snapshotted once, never re-read, because --write makes files dirty as it
    goes: network-map.md holds TWO generated blocks, and a per-write check
    would let the first block land and then refuse the second on the
    dirtiness the pass itself had just created.
    """
    rc, out, _ = _run(["git", "status", "--porcelain"], repo_dir, timeout=30)
    if rc != 0:
        return None
    return {line[3:].split(" -> ")[-1].strip().strip('"') for line in out.splitlines() if line[3:]}


def _blocked(dirty, dest):
    """Is dest carrying uncommitted work this pass must not clobber?"""
    if dirty is None:
        return "git status could not be read"
    for p in dirty:
        if p == dest or p.startswith(dest.rstrip("/") + "/"):
            return f"{p} has uncommitted changes"
    return None


def _block_text(path: Path, marker: str):
    if not path.is_file():
        return None, f"no committed file at {path}"
    txt = path.read_text(encoding="utf-8", errors="replace")
    a = txt.find(f"<!-- {marker}:start -->")
    b = txt.find(f"<!-- {marker}:end -->")
    if a < 0 or b < 0 or b < a:
        return None, f"no <!-- {marker} --> block in {path}"
    return txt[a + len(f"<!-- {marker}:start -->"):b].strip("\n"), None


def _splice(path: Path, marker: str, body: str):
    txt = path.read_text(encoding="utf-8", errors="replace")
    s = f"<!-- {marker}:start -->"
    e = f"<!-- {marker}:end -->"
    a, b = txt.find(s), txt.find(e)
    path.write_text(txt[:a + len(s)] + "\n" + body.strip("\n") + "\n" + txt[b:], encoding="utf-8")


def _diff(old, new, n=6):
    d = [x for x in difflib.unified_diff(old.splitlines(), new.splitlines(),
                                         "committed", "fresh", lineterm="", n=0)
         if x[:1] in "+-" and not x.startswith(("+++", "---"))]
    return d[:n], len(d)


# ---------------------------------------------------------------- strategies


def _do_block(a: Artifact, repo_dir: Path, write: bool, dirty):
    dest = repo_dir / a.dest
    have, why = _block_text(dest, a.marker)
    if have is None:
        # Fail closed. A committed artifact whose markers cannot be found is
        # not an artifact that matches; it is one nothing can regenerate.
        return Result(a, Status.UNKNOWN, f"{why} -- cannot compare, NOT unchanged", reached=False)

    argv, why = _resolve(a.cmd, repo_dir)
    if argv is None:
        return Result(a, Status.UNKNOWN, f"{why} -- NOT unchanged", reached=False)
    rc, out, err = _run(argv, repo_dir)
    bad = _classify_generator(rc, err, a.source)
    if bad:
        st, detail = bad
        return Result(a, st, detail, reached=(st is not Status.UNKNOWN))

    fresh = out.strip()
    if have.strip() == fresh:
        return Result(a, Status.OK, f"unchanged (source: {a.source})")

    sample, n = _diff(have.strip(), fresh)
    if not write:
        return Result(a, Status.WARNING,
                      f"{n} line(s) would change -- --write to apply", sample)
    block = _blocked(dirty, a.dest)
    if block:
        return Result(a, Status.WARNING,
                      f"{n} line(s) stale but NOT written -- {block}", sample)
    _splice(dest, a.marker, out)
    return Result(a, Status.OK, f"regenerated, {n} line(s) changed -- {a.land}", sample)


def _do_tool(a: Artifact, repo_dir: Path, write: bool, dirty):
    argv, why = _resolve(a.cmd, repo_dir)
    if argv is None:
        return Result(a, Status.UNKNOWN, f"{why} -- NOT unchanged", reached=False)
    rc, out, err = _run(argv, repo_dir)
    bad = _classify_generator(rc, err, a.source)
    if bad:
        st, detail = bad
        return Result(a, st, detail, reached=(st is not Status.UNKNOWN))

    if re.search(a.current_re, out, re.M):
        return Result(a, Status.OK, f"unchanged (source: {a.source})")

    summary = _tool_summary(out, a.stale_re)
    if not write:
        return Result(a, Status.WARNING, f"{summary} -- --write to apply")
    block = _blocked(dirty, a.dest)
    if block:
        return Result(a, Status.WARNING, f"{summary}, NOT written -- {block}")
    wrc, wout, werr = _run(argv + a.write_args, repo_dir)
    if wrc != 0:
        why = ([x for x in (werr or wout).strip().splitlines() if x.strip()] or [""])[-1]
        return Result(a, Status.CRITICAL, f"--write failed, exit {wrc} -- {why[:160]}")
    return Result(a, Status.OK, f"regenerated ({summary}) -- {a.land}")


def _tool_summary(out, pattern):
    """The generator's own sentence about what would change, not a new one.

    The pattern is declared per artifact and anchored to a WHOLE line. A
    loose keyword scan across the whole dry run reads the generator's own
    CONTENT: measured 2026-09-08, a "stale" scan quoted the changelog entry
    "regenerate hee/INDEX.md, stale since the identity-block sweep" as if it
    were the tool's verdict.
    """
    m = re.search(pattern, out, re.M) if pattern else None
    return _STATUS_PREFIX.sub("", m.group(0).strip()) if m else "would change"


def _do_publish(a: Artifact, repo_dir: Path, write: bool, dirty):
    """Render, then ask the host what it is actually serving.

    There is no committed copy of this artifact, so the only honest baseline
    is the page itself. Deploying is deliberately NOT done here even under
    --write: pushing to a host is landing, and landing is an operator action.
    """
    argv, why = _resolve(a.cmd, repo_dir)
    if argv is None:
        return Result(a, Status.UNKNOWN, f"{why} -- NOT unchanged", reached=False)
    script = argv[0]

    env_note = os.environ.get("HEE_BRANDING")
    with tempfile.TemporaryDirectory(prefix="hee-regen-") as tmp:
        js = Path(tmp) / "old-commits.json"
        rc, out, err = _run([script, "collect", "--out", str(js)], repo_dir)
        bad = _classify_generator(rc, err, "the org's origin branches (git + gh)")
        if bad:
            st, detail = bad
            return Result(a, st, detail, reached=(st is not Status.UNKNOWN))
        if not env_note:
            os.environ["HEE_BRANDING"] = str(Path.home() / "git/tcos-audit/policy/branding.card.v1.yaml")
        rc, out, err = _run([script, "render", str(js), "--out", tmp], repo_dir)
        if not env_note:
            os.environ.pop("HEE_BRANDING", None)
        bad = _classify_generator(rc, err, "the renderer")
        if bad:
            st, detail = bad
            return Result(a, st, detail, reached=(st is not Status.UNKNOWN))
        fresh = (Path(tmp) / "old-commits.html").read_text(encoding="utf-8", errors="replace")
        staged = None
        if write:
            staged = Path(tempfile.gettempdir()) / "hee-regen" / "old-commits.html"
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(tmp) / "old-commits.html", staged)

    live = _fetch(a.published_url)
    if live is None:
        return Result(a, Status.UNKNOWN,
                      f"rendered, but {a.published_url} could not be read -- "
                      f"published state unknown, NOT unchanged", reached=False)

    if _ISO.sub("<ts>", live) == _ISO.sub("<ts>", fresh):
        return Result(a, Status.OK, f"published page matches a fresh render (source: {a.source})")

    when = _published_stamp(live)
    tail = f" -- publish with `{a.land}` (a deploy, not a write: this pass never deploys)"
    if staged:
        tail = f" -- staged at {staged}{tail}"
    return Result(a, Status.WARNING,
                  "published page differs from a fresh render"
                  + (f" (published {when})" if when else "") + tail)


def _fetch(url):
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(url, timeout=20, context=ctx) as r:
            return r.read().decode("utf-8", "replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return None


# The sentence the page writes about ITSELF -- "as fetched from HOST at ISO".
# Preferred over "the first timestamp in the file", which is only right by
# accident and would silently start naming a chrome build stamp the day the
# renderer grows one.
_FETCHED_AT = re.compile(r"as fetched from .{0,120}? at (" + _ISO.pattern + ")")


def _published_stamp(html):
    m = _FETCHED_AT.search(html)
    if m:
        return m.group(1)
    m = _ISO.search(html)
    return m.group(0) if m else ""


STRATEGY = {"block": _do_block, "tool": _do_tool, "publish": _do_publish}


# ---------------------------------------------------------------- the pass


def run_pass(repos, write=False, git_root=None):
    """Regenerate (or, by default, just report on) every declared artifact.

    ``repos`` is a list of repo directories in scope; ``None`` means every
    repo the registry declares, whether or not it is checked out -- a
    declared artifact with no checkout is UNKNOWN, not absent.
    """
    root = Path(git_root or os.environ.get("HEE_GIT_ROOT") or (Path.home() / "git"))
    if repos is None:
        wanted = {a.repo: root / a.repo for a in ARTIFACTS}
    else:
        wanted = {_identity(Path(d)): Path(d) for d in repos}

    dirty_by_repo = {}
    results = []
    for a in ARTIFACTS:
        if a.repo not in wanted:
            continue
        repo_dir = wanted[a.repo]
        if not (repo_dir / ".git").exists():
            results.append(Result(a, Status.UNKNOWN,
                                  f"no checkout at {repo_dir} -- NOT unchanged", reached=False))
            continue
        if a.repo not in dirty_by_repo:
            dirty_by_repo[a.repo] = _dirty(repo_dir)
        results.append(STRATEGY[a.kind](a, repo_dir, write, dirty_by_repo[a.repo]))
    return results


def report(results, write, out=sys.stdout):
    """One ordered block on ONE stream.

    Deliberately not hee_status.emit(), which splits OK to stdout and
    everything else to stderr. That is right for a single verdict and wrong
    for a report: interleaved, the lines arrive out of order and the reader
    cannot tell which artifact a finding belongs to.
    """
    if not write:
        print("DRY RUN -- nothing will be written. Add --write to apply.", file=out)
    print("", file=out)
    for r in results:
        print(render(r.status, f"{r.artifact.repo}/{r.artifact.label}: {r.detail}"), file=out)
        for line in r.diff:
            print(f"     {line}", file=out)

    n = len(results)
    ok = sum(1 for r in results if r.status is Status.OK)
    stale = sum(1 for r in results if r.status is Status.WARNING)
    unknown = sum(1 for r in results if r.status is Status.UNKNOWN)
    crit = sum(1 for r in results if r.status is Status.CRITICAL)
    print("", file=out)
    print(f"{n} declared artifact(s): {ok} current, {stale} stale, "
          f"{unknown} unreadable, {crit} broken", file=out)

    # Say WHICH sources were not reached. A pass that quietly returns a
    # shorter list is the failure this whole tool exists to avoid.
    missed = sorted({r.artifact.source for r in results if not r.reached})
    if missed:
        print(render(Status.UNKNOWN,
                     "source(s) not reached, so their artifacts were NOT judged: "
                     + "; ".join(missed)), file=out)

    if crit:
        return Status.CRITICAL
    if unknown:
        return Status.UNKNOWN
    if stale:
        return Status.WARNING
    return Status.OK


def main(argv):
    write = "--write" in argv
    args = [a for a in argv if a != "--write"]
    git_root = None
    repos = []
    all_declared = False
    while args:
        a = args.pop(0)
        if a == "--all":
            all_declared = True
        elif a == "--git-root":
            git_root = args.pop(0)
        elif a.startswith("-"):
            print(f"hee_regen: unknown option {a}", file=sys.stderr)
            return Status.UNKNOWN.value
        else:
            repos.append(a)
    results = run_pass(None if all_declared or not repos else repos, write=write, git_root=git_root)
    if not results:
        print(render(Status.OK, "no repo in scope declares a generated artifact"))
        return Status.OK.value
    return report(results, write).value
