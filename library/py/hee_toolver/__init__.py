"""hee_toolver -- determine a tool's version, and prove it is a version.

Why this exists
---------------
Two real defects, 2026-08-31, both from guessing instead of validating:

1. `sh --version` prints ``sh: 0: Illegal option --`` and exits 2. A naive
   probe recorded that error message AS the version string. It even
   replayed consistently, because the error is deterministic -- so
   "it reproduces" was not enough to catch it.

2. `tmux --version` is not a tmux flag; tmux uses ``-V``. A Makefile used
   ``--version`` and captured the usage block instead of a version.

So a version claim needs two things a bare probe does not give:
  * a NON-ZERO EXIT IS NEVER A VERSION, and
  * the captured text must actually LOOK like a version.

VERSION_RE requires at least ``<digits>.<digits>``. That is what separates
``tmux 3.4`` and ``jq-1.7`` from ``sh: 0: Illegal option --``, which
contains a digit but no dotted version.

Flag discovery
--------------
When a tool answers none of the usual flags, `discover_flag` reads its own
``-h``/``--help`` and looks for a documented version option rather than
brute-forcing further. That is how a tool like tmux tells you it wants
``-V``, if you bother to ask it.

Never runs a tool with no argument. `hee-gen-manpages` was observed
installing a pre-commit hook as a side effect of generating documentation
(issue 464); this library only ever passes an explicit flag.
"""

from __future__ import annotations

import re
import os
import shutil
import subprocess
from dataclasses import dataclass

__all__ = ["VERSION_RE", "Probe", "looks_like_version", "probe", "discover_flag"]

# At least major.minor. A bare digit is not a version -- that is exactly the
# shape of "sh: 0: Illegal option --".
#
# The lookbehind excludes only digits and dots, NOT letters: a leading "v" is
# extremely common ("version v4.53.3") and an earlier stricter lookbehind
# rejected yq's real version for exactly that reason, then fell through to
# `yq -v` -- which on yq means VERBOSE, not version. That turned on debug
# logging and emitted a timestamp, from which a "version" of 16.691-05 was
# extracted. Two failures compounding: a wrongly-rejected good answer, then
# a wrongly-accepted bad one.
VERSION_RE = re.compile(r"(?<![\d.])v?\d+\.\d+(?:\.\d+)*(?:[-+~][\w.]+)?(?![\d.])")

# A timestamp contains dotted digits and will otherwise satisfy VERSION_RE.
# Reject before matching rather than after, so a verbose-mode log line can
# never be mistaken for a version.
_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}|\d{2}:\d{2}:\d{2}")

# -v is DELIBERATELY ABSENT. Measured 2026-08-31 across 17 tools: not one
# needs it for version detection, and on twelve it means something else --
# verbose (yq, python3, curl), invert-match (grep, rg), assign-variable
# (awk), a plain error (sed, jq, gh), or an entirely different fact
# (uname -v is the KERNEL build string, not uname's version).
#
# Two real failures came from including it. `yq -v` enabled debug logging
# and printed a timestamp, from which "16.691-05" was extracted. `uname -v`
# returns "#28~24.04.1-Ubuntu SMP ... 15:50:57 UTC" -- rejected only
# because the timestamp guard fired, not because the version pattern
# refused it; the raw pattern happily matched "24.04.1-Ubuntu". A kernel
# string without a time in it would have been recorded as a version.
#
# -V is the conventional short version flag and is kept. A tool that truly
# needs lowercase -v can be handled by discover_flag reading its own help.
CANDIDATE_FLAGS = ("--version", "-V", "version")
HELP_FLAGS = ("--help", "-h", "-?")

# In a help text, a line mentioning version is expected to name its flag.
_HELP_VERSION_LINE = re.compile(
    r"^\s*(?P<flags>-[-\w?]+(?:\s*,\s*-[-\w?]+)*)\s+.*\bversion\b", re.IGNORECASE | re.MULTILINE
)


@dataclass(frozen=True)
class Probe:
    tool: str
    path: str | None
    flag: str | None        # the flag that actually worked
    raw: str | None         # first line captured
    version: str | None     # the substring matching VERSION_RE
    stream: str | None      # stdout | stderr
    returncode: int | None
    reason: str             # why this outcome, in words


def looks_like_version(text: str) -> str | None:
    """Return the version substring, or None. Never guesses."""
    if not text:
        return None
    if _TIMESTAMP_RE.search(text):
        return None
    m = VERSION_RE.search(text)
    return m.group(0).lstrip("vV") if m else None


def _run(argv: list[str], timeout: int = 5):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None


def discover_flag(path: str) -> str | None:
    """Ask the tool's own help which flag reports its version."""
    for hf in HELP_FLAGS:
        r = _run([path, hf])
        if r is None:
            continue
        text = (r.stdout or "") + (r.stderr or "")
        if not text.strip():
            continue
        for m in _HELP_VERSION_LINE.finditer(text):
            for f in re.split(r"\s*,\s*", m.group("flags").strip()):
                if f.startswith("-"):
                    return f
    return None


def probe(tool: str, extra_flags: tuple[str, ...] = ()) -> Probe:
    path = shutil.which(tool)
    if not path:
        return Probe(tool, None, None, None, None, None, None, "not installed")

    tried: list[str] = []
    for flag in tuple(extra_flags) + CANDIDATE_FLAGS:
        if flag in tried:
            continue
        tried.append(flag)
        r = _run([path, flag])
        if r is None:
            continue
        if r.returncode != 0:
            continue                      # an error is never a version
        for stream, txt in (("stdout", r.stdout), ("stderr", r.stderr)):
            line = next((l.strip() for l in (txt or "").splitlines() if l.strip()), "")
            if not line:
                continue
            ver = looks_like_version(line)
            if ver:
                return Probe(tool, path, flag, line, ver, stream, r.returncode,
                             "matched VERSION_RE on a zero-exit invocation")

    # Nothing standard worked -- ask the tool's own help what it wants.
    found = discover_flag(path)
    if found and found not in tried:
        r = _run([path, found])
        if r is not None and r.returncode == 0:
            for stream, txt in (("stdout", r.stdout), ("stderr", r.stderr)):
                line = next((l.strip() for l in (txt or "").splitlines() if l.strip()), "")
                ver = looks_like_version(line) if line else None
                if ver:
                    return Probe(tool, path, found, line, ver, stream, r.returncode,
                                 f"flag discovered from the tool's own help: {found}")

    return Probe(tool, path, None, None, None, None, None,
                 f"no flag produced a string matching VERSION_RE (tried: {', '.join(tried)}"
                 + (f"; help suggested {found}" if found else "; help suggested nothing") + ")")


# ---------------------------------------------------------------------------
# Platform and package provenance -- portable, not Debian-only.
#
# Operator: "whatever the bsds and other common, use a grep on os-release for
# versions too, support all versions" and "lsb_release can be useful too on
# s0ome".
#
# Sources are tried in order of reliability, and EVERY source that answers is
# recorded, not just the first. They disagree in useful ways -- on this host
# os-release says Linux Mint 22.2 while every package carries an Ubuntu
# 24.04 version string, because Mint is Ubuntu-derived. Keeping only one
# would lose that.
#
#   /etc/os-release        freedesktop standard: most Linux, and FreeBSD 13+,
#                          NetBSD, DragonFly. Also /usr/lib/os-release.
#   lsb_release -a         older Debian/Ubuntu/RHEL where os-release is thin
#   sw_vers                macOS
#   freebsd-version        FreeBSD (kernel vs userland differ after patching)
#   uname -sr              always available, lowest common denominator
# ---------------------------------------------------------------------------

OS_RELEASE_PATHS = ("/etc/os-release", "/usr/lib/os-release",
                    "/etc/lsb-release", "/etc/openwrt_release")

# Package managers, in the order they are tried. Each maps a real file path to
# the package owning it. Only ones actually present on the host are used.
PKG_QUERIES = (
    ("dpkg",    ["dpkg", "-S"],            ["dpkg-query", "-W", "-f=${Version}"]),
    ("rpm",     ["rpm", "-qf"],            ["rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}"]),
    ("pacman",  ["pacman", "-Qo"],         ["pacman", "-Q"]),
    ("apk",     ["apk", "info", "-W"],     ["apk", "info", "-v"]),
    ("pkg",     ["pkg", "which", "-q"],    ["pkg", "query", "%v"]),        # FreeBSD
    ("brew",    ["brew", "--prefix"],      ["brew", "list", "--versions"]),
)


def _read_os_release() -> dict:
    """Parse every os-release-shaped file present. Later files do not clobber."""
    data: dict[str, str] = {}
    for path in OS_RELEASE_PATHS:
        try:
            with open(path) as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    data.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except OSError:
            continue
    return data


def platform() -> dict:
    """Everything the host will tell us about itself. Never raises."""
    out: dict = {"sources": []}

    osr = _read_os_release()
    if osr:
        out["sources"].append("os-release")
        out["distro"] = osr.get("PRETTY_NAME") or osr.get("DISTRIB_DESCRIPTION") or ""
        out["distro_id"] = osr.get("ID") or osr.get("DISTRIB_ID") or ""
        out["distro_version"] = osr.get("VERSION_ID") or osr.get("DISTRIB_RELEASE") or ""
        for k in ("VERSION_CODENAME", "ID_LIKE", "BUILD_ID", "VARIANT_ID"):
            if osr.get(k):
                out[k.lower()] = osr[k]

    r = _run(["lsb_release", "-a"])
    if r is not None and r.returncode == 0 and r.stdout.strip():
        out["sources"].append("lsb_release")
        for line in r.stdout.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out.setdefault("lsb_" + k.strip().lower().replace(" ", "_"), v.strip())

    r = _run(["sw_vers"])                                   # macOS
    if r is not None and r.returncode == 0 and r.stdout.strip():
        out["sources"].append("sw_vers")
        for line in r.stdout.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out["macos_" + k.strip().lower().replace(" ", "_")] = v.strip()

    r = _run(["freebsd-version", "-kru"])                   # FreeBSD
    if r is not None and r.returncode == 0 and r.stdout.strip():
        out["sources"].append("freebsd-version")
        parts = r.stdout.split()
        for label, val in zip(("kernel", "running", "userland"), parts):
            out["freebsd_" + label] = val

    for label, args in (("kernel_name", ["uname", "-s"]),
                        ("kernel_release", ["uname", "-r"]),
                        ("arch", ["uname", "-m"])):
        r = _run(["uname", args[1]])
        if r is not None and r.returncode == 0:
            out[label] = r.stdout.strip()
    out["sources"].append("uname")

    r = _run(["ldd", "--version"])                          # glibc / musl
    if r is not None and r.stdout.strip():
        out["libc"] = r.stdout.splitlines()[0].strip()

    return out


def package_for(path: str) -> tuple[str | None, str | None, str | None]:
    """(manager, package, package_version) for a binary, or (None, None, None).

    Tries every package manager present. A host can have more than one -- a
    brew binary on a dpkg system, for instance -- so the FIRST that claims the
    file wins, and the manager name is recorded alongside so the answer is
    never ambiguous about where it came from.
    """
    if not path:
        return None, None, None
    real = os.path.realpath(path)
    for name, owns, ver in PKG_QUERIES:
        if not shutil.which(owns[0]):
            continue
        r = _run(owns + [real])
        if r is None or r.returncode != 0 or not r.stdout.strip():
            continue
        line = r.stdout.strip().splitlines()[0]
        pkg = line.split(":")[0].strip() if name == "dpkg" else line.split()[0].strip()
        if not pkg:
            continue
        v = _run(ver + [pkg])
        pv = None
        if v is not None and v.returncode == 0 and v.stdout.strip():
            pv = v.stdout.strip().splitlines()[0].split()[-1]
        return name, pkg, pv
    return None, None, None


# ---------------------------------------------------------------------------
# Three independent sources of a tool's version. They disagree, and each is
# right about a different thing:
#
#   self     what the binary says about itself (--version). Authoritative for
#            behavior, but tools lie: jq reports 1.7 while the installed
#            package is 1.7.1.
#   package  what the package manager has installed. Authoritative for
#            provenance and patching -- carries distro patch levels and epochs
#            (git: 1:2.43.0-1ubuntu7.3) the binary never mentions.
#   path     the version encoded in the install path. Often the ONLY source
#            for version-managed runtimes: nvm puts node at
#            .../node/v20.20.2/bin/node, and /usr/bin/python3.12 names it in
#            the binary itself.
#
# Callers choose with source=. Default "auto" tries self, then path, then
# package -- and records which answered.
# ---------------------------------------------------------------------------

SOURCES = ("auto", "self", "package", "path")

# Version in a path segment or a versioned binary name. Kept RE2-safe so the
# same expression is usable from sh -- see library/regex/patterns.yaml.
_PATH_VERSION = re.compile(r"(^|[^0-9.])v?([0-9]+\.[0-9]+(\.[0-9]+)?)([^0-9.]|$)")


def version_from_path(path: str) -> str | None:
    """Version encoded in the install path, e.g. .../node/v20.20.2/bin/node.

    Walks segments from the deepest, so a versioned binary name wins over a
    versioned parent directory -- /usr/lib/python3/bin/python3.12 should give
    3.12, not 3.
    """
    if not path:
        return None
    for seg in reversed(os.path.realpath(path).split(os.sep)):
        m = _PATH_VERSION.search(seg)
        if m:
            return m.group(2)
    return None


def version_of(tool: str, source: str = "auto") -> dict:
    """Version of `tool` from the chosen source, with every source recorded.

    Returns the answer plus every source that had an opinion, and flags
    disagreement rather than silently preferring one.
    """
    if source not in SOURCES:
        raise ValueError(f"source must be one of {SOURCES}, got {source!r}")

    path = shutil.which(tool)
    p = probe(tool)
    mgr, pkg, pkg_ver = package_for(path) if path else (None, None, None)
    path_ver = version_from_path(path) if path else None

    found = {"self": p.version, "package": pkg_ver, "path": path_ver}
    order = ("self", "path", "package") if source == "auto" else (source,)
    chosen = next((s for s in order if found.get(s)), None)

    real = [s for s, v in found.items() if v]
    # A coarser answer is not a disagreement. An install path usually encodes
    # only major.minor (/usr/bin/python3.12) while the binary reports
    # major.minor.patch -- 3.12 vs 3.12.3 is the same tool, described less
    # precisely. Only a genuine conflict counts.
    def compat(a, b):
        return a == b or a.startswith(b + ".") or b.startswith(a + ".")

    cs, cpk, cpath = _core(p.version or ""), _core(pkg_ver or ""), _core(path_ver or "")
    # A CONFLICT is a genuine mismatch -- neither is a refinement of the other.
    conflict = any(not compat(a, b) for a in (cs, cpk, cpath) if a
                                     for b in (cs, cpk, cpath) if b)
    # IMPRECISE is one source being coarser. Expected from a path
    # (/usr/bin/python3.12 encodes only major.minor) and not worth flagging.
    # Between the BINARY and the PACKAGE it is worth flagging: jq reports 1.7
    # while 1.7.1 is installed, so the binary under-reports itself.
    imprecise = bool(cs and cpk and cs != cpk and compat(cs, cpk))
    disagree = conflict

    return {
        "tool": tool, "path": path,
        "source_requested": source,
        "source_used": chosen,
        "version": found.get(chosen) if chosen else None,
        "self": p.version, "self_flag": p.flag, "self_raw": p.raw,
        "package": pkg_ver, "package_name": pkg, "package_manager": mgr,
        "path_version": path_ver,
        "sources_answering": real,
        "disagree": disagree,
        "conflict": conflict,
        "imprecise": imprecise,
        "reason": p.reason,
    }


def _core(v: str) -> str:
    """Comparable core of a version -- strips a dpkg epoch and any suffix."""
    v = re.sub(r"^\d+:", "", v or "")
    m = re.match(r"[0-9]+(\.[0-9]+)*", v)
    return m.group(0) if m else v



# ---------------------------------------------------------------------------
# Hardware / firmware discovery.
#
# Operator: "support dmidecode and bios detecatico, etc too".
#
# PREFER SYSFS, NOT dmidecode. /sys/class/dmi/id/* exposes the same SMBIOS
# fields and is readable UNPRIVILEGED; dmidecode reads
# /sys/firmware/dmi/tables/smbios_entry_point and fails with Permission
# denied as a normal user. Verified on kiosk 2026-08-31. That matches
# docs/specs/HEE_HARDWARE_DISCOVERY.md's own stated principles --
# read_only_by_default and least_privilege -- so needing root to read a BIOS
# date is a reason to use a different source, not a reason to escalate.
#
# Serial numbers are deliberately NOT collected. product_serial,
# board_serial and product_uuid are root-only precisely because they
# identify a specific machine; they are provenance nobody asked for and a
# privacy problem if they land in a git repo.
# ---------------------------------------------------------------------------

DMI_SYSFS = "/sys/class/dmi/id"
DMI_FIELDS = ("sys_vendor", "product_name", "product_version",
              "board_vendor", "board_name", "board_version",
              "bios_vendor", "bios_version", "bios_date",
              "chassis_type", "chassis_vendor")

# SMBIOS 3.x chassis types -- the common ones. A bare number is useless in a
# report, and "3" appearing where a human expects a word is how a field gets
# ignored.
CHASSIS_TYPES = {
    "1": "Other", "2": "Unknown", "3": "Desktop", "4": "Low Profile Desktop",
    "6": "Mini Tower", "7": "Tower", "8": "Portable", "9": "Laptop",
    "10": "Notebook", "13": "All In One", "17": "Main Server Chassis",
    "23": "Rack Mount Chassis", "30": "Tablet", "31": "Convertible",
    "32": "Detachable", "35": "Mini PC",
}


def hardware() -> dict:
    """Host hardware and firmware facts. Unprivileged sources only."""
    out: dict = {"sources": []}

    dmi: dict[str, str] = {}
    for f in DMI_FIELDS:
        try:
            with open(os.path.join(DMI_SYSFS, f)) as fh:
                v = fh.read().strip()
            if v and v.lower() not in ("to be filled by o.e.m.", "default string", "none"):
                dmi[f] = v
        except OSError:
            continue
    if dmi:
        out["sources"].append("sysfs-dmi")
        out.update(dmi)
        if "chassis_type" in dmi:
            out["chassis"] = CHASSIS_TYPES.get(dmi["chassis_type"], f"code {dmi['chassis_type']}")

    # dmidecode only as a fallback, and only if it actually works unprivileged.
    if not dmi and shutil.which("dmidecode"):
        r = _run(["dmidecode", "-s", "bios-version"])
        if r is not None and r.returncode == 0 and r.stdout.strip():
            out["sources"].append("dmidecode")
            out["bios_version"] = r.stdout.strip()

    try:
        with open("/proc/cpuinfo") as fh:
            for line in fh:
                if line.startswith("model name"):
                    out["cpu_model"] = line.split(":", 1)[1].strip()
                    break
        out["sources"].append("procfs")
    except OSError:
        pass
    try:
        out["cpu_count"] = str(os.cpu_count() or "")
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    out["mem_total_gb"] = f"{int(line.split()[1]) / 1048576:.1f}"
                    break
    except OSError:
        pass

    r = _run(["systemd-detect-virt"])
    if r is not None and r.stdout.strip():
        out["virtualization"] = r.stdout.strip()  # US English (operator standing rule)

    return out


# ---------------------------------------------------------------------------
# Session / agent identity.
#
# Operator: "hee ver should also handle the tmux, env, etc for the agent sig
# too". These are the fields contracts/agent-instance-signature-v1.contract
# .yaml requires -- session_id, host, gh_actor, timestamp, tmux -- so `hee
# ver` can produce the signature block rather than a second tool duplicating
# the same probes.
#
# Every field is read from THIS process's own environment. Nothing is
# invented and nothing is centrally issued, which is the contract's own
# stated requirement.
# ---------------------------------------------------------------------------

def session() -> dict:
    """Facts identifying this running agent instance."""
    import datetime, socket

    out = {
        "session_id": os.environ.get("CLAUDE_CODE_SESSION_ID", "unknown"),
        "session_kind": "agent" if os.environ.get("CLAUDE_CODE_SESSION_ID") else "human",
        "pid": str(os.getpid()),
        "host": socket.getfqdn(),
        "user": os.environ.get("USER") or os.environ.get("LOGNAME") or "unknown",
        "timestamp": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "shell": os.environ.get("SHELL", "unknown"),
        "term": os.environ.get("TERM", "unknown"),
    }

    tmux = os.environ.get("TMUX")
    if tmux:
        socket_path = tmux.split(",", 1)[0]
        out["tmux_socket"] = socket_path
        pane = os.environ.get("TMUX_PANE", "")
        out["tmux_pane"] = pane or "unknown"

        # -t "$TMUX_PANE" is load-bearing, not defensive. Without it tmux
        # answers for the ACTIVE pane of the attached client, which is a
        # different pane than the one this process runs in whenever the
        # operator is looking somewhere else. Measured on kiosk 2026-09-02:
        # this process was %1 (main:0.0) while the active pane was %2
        # (main:0.1), and the bare query returned the active pane's session.
        # Paired with tmux_pane read from the environment, that produced a
        # tmux_uri assembled from two different panes -- correct only by
        # luck when both sat in the same session, and naming a
        # session/pane pair that does not exist when they did not.
        target = ["-t", pane] if pane else []
        fmt = "#{session_name}\t#{window_index}\t#{pane_index}\t#{client_termfeatures}"
        r = _run(["tmux", "display", "-p", *target, fmt])
        if r and r.returncode == 0:
            f = (r.stdout.rstrip("\n").split("\t") + ["", "", "", ""])[:4]
            sess, win, idx, feats = f
        else:
            sess, win, idx, feats = "unknown", "", "", ""

        out["tmux_session"] = sess or "unknown"
        out["tmux_uri"] = f"{socket_path}:{out['tmux_session']}:{out['tmux_pane']}"
        # The addressable form -- what `tmux select-pane -t` accepts.
        # %N is a server-lifetime handle and does not survive a restart.
        out["tmux_target"] = (
            f"{sess}:{win}.{idx}" if sess and win != "" and idx != "" else "unknown"
        )
        # Hyperlink support decides whether tool output can use OSC 8 at all.
        out["tmux_termfeatures"] = feats
        out["osc8_hyperlinks"] = "yes" if "hyperlinks" in feats else "no"
    else:
        out["tmux_uri"] = "none"

    # rc_tag -- one readable label for THIS running instance.
    #
    # Operator, 2026-09-02: "if there is no tmux, then there is no tmux
    # string" -- the tmux segment is omitted entirely rather than filled
    # with a placeholder.
    #
    # Deliberately NOT built from $TMUX_SESSION. That variable lives in
    # tmux's GLOBAL environment here, one shared value inherited by every
    # pane in every session, so it structurally cannot track a session
    # name: measured, it read "kiosk" for a pane that was in "main".
    #
    # The session-id segment is what actually disambiguates two concurrent
    # agents on one host, which is the incident
    # contracts/agent-instance-signature-v1.contract.yaml exists for. Per
    # that contract's extension-path, this composes the identifiers the
    # fleet already has rather than starting another scheme, and per the
    # SOA anchor's own "short_token_never_authoritative" invariant it is a
    # label, never the authority.
    # The base is ALWAYS host-user-sessionid, and the tmux location is
    # APPENDED after "_" rather than inserted in the middle. Operator,
    # 2026-09-02: "always use the full like so, it is easier to sort".
    #
    #     kiosk-claude-0f41d560              no tmux
    #     kiosk-claude-0f41d560_main:0.0     in tmux
    #
    # That is the point of the shape: every tag for a given host, user and
    # instance shares one prefix, so a sort groups them and the tmux
    # location never shifts the session id to a different column. An
    # earlier draft interleaved them (host-user-TARGET-sessionid), which
    # sorted the two forms apart.
    # A human shell has no CLAUDE_CODE_SESSION_ID, and 2026-09-06 its rc_tag
    # came out as a bare "kiosk-spencer": no instance segment, so two of the
    # operator's shells -- or two days of them -- were indistinguishable in
    # a deploy record signed with it. Derive one the same way the fleet
    # identifies a login: the logind session id when pam_systemd set it,
    # else the controlling tty plus the login shell's start time; hashed so
    # it has the agent form's shape (8 hex) and sorts beside it.
    if out["session_id"] == "unknown":
        import hashlib
        # First choice, operator 2026-09-06: "should use index/_.yaml [when
        # it] is defined" -- the oper's SOA anchor (~/.hee/index/_.yaml,
        # hee-soa.v1). Its stool hash IS this oper-on-this-host's durable
        # identity; a label built from it composes what the fleet already
        # has (contract extension-path) instead of inventing a seed. Still
        # a label, never the authority (short_token_never_authoritative).
        anchor = os.path.join(os.path.expanduser("~"), ".hee", "index", "_.yaml")
        soa = None
        if os.path.isfile(anchor):
            try:
                import yaml
                soa = (yaml.safe_load(open(anchor)) or {}).get("yaml.v0", {}).get("hee_soa") or None
            except Exception:
                soa = None
        if soa and soa.get("stool_hash_full"):
            out["session_id"] = "soa-" + str(soa["stool_hash_full"])[:8]
            out["session_seed"] = "soa-anchor"
            out["soa_anchor"] = anchor
            if soa.get("host") and soa["host"] != out["host"] or soa.get("user") and soa["user"] != out["user"]:
                out["soa_mismatch"] = f"anchor says {soa.get('user')}@{soa.get('host')}, running as {out['user']}@{out['host']}"
        seed = "" if soa and soa.get("stool_hash_full") else (os.environ.get("XDG_SESSION_ID") or "")
        if not seed and out["session_id"] == "unknown":
            try:
                tty = os.ttyname(0) if os.isatty(0) else ""
            except OSError:
                tty = ""
            r = _run(["ps", "-o", "lstart=", "-p", str(os.getppid())])
            seed = f"{tty}|{(r.stdout if r else '').strip()}"
        if seed.strip("|"):
            out["session_id"] = "human-" + hashlib.sha256(f"{out['host']}|{out['user']}|{seed}".encode()).hexdigest()[:8]
            out["session_seed"] = "logind" if os.environ.get("XDG_SESSION_ID") else "tty+login-time"
    sid8 = out["session_id"].split("-", 1)[1][:8] if out["session_id"].startswith(("human-", "soa-")) else out["session_id"][:8]
    base = "-".join(
        p for p in (
            out["host"].split(".", 1)[0] or out["host"],
            out["user"],
            sid8 if out["session_id"] != "unknown" else "",
        ) if p
    )
    target = out.get("tmux_target", "unknown")
    out["rc_tag"] = f"{base}_{target}" if target != "unknown" else base

    r = _run(["gh", "auth", "status"])
    if r is not None:
        m = re.search(r"account (\S+)", (r.stdout or "") + (r.stderr or ""))
        out["gh_actor"] = m.group(1) if m else "unknown"

    r = _run(["git", "config", "user.email"])
    if r is not None and r.returncode == 0:
        out["git_identity"] = r.stdout.strip()

    return out


# ---------------------------------------------------------------------------
# fs-verity.
#
# Read hee/docs/IMPLEMENTATION_MANUAL-partial.md before changing this. The
# org's design does NOT want a boolean -- it wants the DIGEST:
#
#   "The file's unique fs-verity digest is compiled directly into your SNMP
#    MIB tree as a static, unalterable identifier for that exact state of
#    logic."
#   "a lookup for nuc1-claude._agents.yourdomain.org returns its public key
#    string or fs-verity root digest"
#   drift check: "asserting fsverity digest /hee/contracts/* matches the
#    reference states mapped inside your local SNMP engine"
#
# So the digest is the product. enabled/disabled is just the precondition.
#
# Read via ioctl, NOT the fsverity CLI. Measured on kiosk 2026-08-31: the
# kernel has CONFIG_FS_VERITY=y and CONFIG_FS_VERITY_BUILTIN_SIGNATURES=y,
# but the fsverity userspace tool is NOT installed. Going through the ioctl
# means this works on a stock node with nothing added -- which is the whole
# low-dependency premise of that manual.
# ---------------------------------------------------------------------------

FS_IOC_GETFLAGS = 0x80086601
FS_VERITY_FL = 0x00100000
# _IOWR('f', 134, struct fsverity_digest) -- struct is two __u16.
FS_IOC_MEASURE_VERITY = 0xC0046686
_VERITY_ALGOS = {1: "sha256", 2: "sha512"}


def verity_of(path: str) -> dict:
    """fs-verity state and digest for a file. Never raises."""
    import fcntl
    import struct

    out = {"path": path, "enabled": False, "digest": None, "algorithm": None,
           "kernel_support": None, "fsverity_cli": bool(shutil.which("fsverity")),
           "error": None}

    try:
        with open(f"/boot/config-{os.uname().release}") as fh:
            out["kernel_support"] = "CONFIG_FS_VERITY=y" in fh.read()
    except OSError:
        out["kernel_support"] = None       # unknown, not false

    if not os.path.exists(path):
        out["error"] = "no such file"
        return out

    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError as e:
        out["error"] = f"cannot open: {e.strerror}"
        return out

    try:
        buf = fcntl.ioctl(fd, FS_IOC_GETFLAGS, struct.pack("L", 0))
        out["enabled"] = bool(struct.unpack("L", buf)[0] & FS_VERITY_FL)
    except OSError as e:
        out["error"] = f"FS_IOC_GETFLAGS: {e.strerror}"

    if out["enabled"]:
        try:
            # digest_algorithm, digest_size, then room for the digest itself
            req = struct.pack("HH", 0, 64) + b"\x00" * 64
            res = fcntl.ioctl(fd, FS_IOC_MEASURE_VERITY, req)
            algo, size = struct.unpack("HH", res[:4])
            out["algorithm"] = _VERITY_ALGOS.get(algo, f"algo-{algo}")
            out["digest"] = res[4:4 + size].hex()
        except OSError as e:
            out["error"] = f"FS_IOC_MEASURE_VERITY: {e.strerror}"

    os.close(fd)
    return out


def verify_records(path: str | None = None) -> dict:
    """Re-run every recorded claim in a primitives registry and check it holds.

    The verify half of ver{sion,ify}. A provenance record is only worth
    keeping if whatever produced it can re-run and still produce it.
    """
    import shlex
    import subprocess as sp

    path = path or os.path.expanduser("~/git/primitives/primitives.yaml")
    try:
        import yaml
        with open(path) as fh:
            doc = yaml.safe_load(fh)
    except Exception as e:
        return {"error": f"cannot read {path}: {e}", "results": [], "ok": 0, "total": 0}

    results = []
    for e in (doc.get("spec", {}).get("entries") or []):
        cmd = (e.get("verified") or {}).get("command", "")
        recorded = e.get("version", "")
        name = e.get("name", "?")
        if not cmd:
            continue
        base = cmd.split("  (")[0]
        try:
            r = sp.run(shlex.split(base), capture_output=True, text=True, timeout=5)
        except Exception as ex:
            results.append({"name": name, "ok": False, "recorded": recorded,
                            "actual": f"could not run: {ex}", "version": None})
            continue
        if "no version" in recorded:
            ok = r.returncode != 0
            results.append({"name": name, "ok": ok, "recorded": recorded,
                            "actual": f"rc={r.returncode}", "version": recorded})
            continue
        line = next((l.strip() for l in ((r.stdout or r.stderr) or "").splitlines()
                     if l.strip()), "")
        actual = looks_like_version(line)
        ok = (r.returncode == 0 and actual == recorded)
        results.append({"name": name, "ok": ok, "recorded": recorded,
                        "actual": actual or line[:40], "version": actual})

    return {"path": path, "results": results,
            "ok": sum(1 for r in results if r["ok"]), "total": len(results)}
