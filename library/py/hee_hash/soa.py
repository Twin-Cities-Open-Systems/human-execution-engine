#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import re
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional


HASH_SPEC_ID = "hee-soa.v1|canon.kv.sort|null.literal|sha256|duople=a:b|stool=concat(duoples)"
HASH_ALGO = "sha256"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _host_short(hostf: str) -> str:
    # host1.example.com -> host1 ; host2.localdomain -> host2
    return hostf.split(".", 1)[0].strip() if hostf else ""


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="strict")


def _parse_expected_stool_from_yaml(yaml_text: str) -> Optional[str]:
    # expects: stool_hash_full: "64hex"
    m = re.search(r'stool_hash_full:\s*\"([0-9a-f]{64})\"', yaml_text)
    return m.group(1) if m else None


def _canon_kv(kv: Dict[str, str]) -> bytes:
    items = []
    for k, v in kv.items():
        kk = k.strip().lower()
        vv = v.strip()
        if vv == "":
            vv = "null"
        items.append((kk, vv))
    items.sort(key=lambda x: x[0])
    out = "".join([f"{k}={v}\n" for k, v in items])
    return out.encode("utf-8")


def _leg_hash(kv: Dict[str, str]) -> str:
    return _sha256_hex(_canon_kv(kv))


def _duople(a: str, b: str) -> str:
    return _sha256_hex(f"{a}:{b}".encode("utf-8"))


def _stool(d_hr: str, d_hu: str, d_ru: str) -> str:
    return _sha256_hex((d_hr + d_hu + d_ru).encode("utf-8"))


def _show(h: str) -> str:
    return f"{h[:8]}..{h[-8:]}"


def parse_legs_kv(text: str) -> Dict[str, Dict[str, str]]:
    """
    Parses .legs.kv format:
      [leg.user]
      k=v
      ...
      [leg.home_fs]
      ...
    Ignores comments (# ...) and blank lines.
    """
    current: Optional[str] = None
    out: Dict[str, Dict[str, str]] = {}

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip().lower()
            if current not in out:
                out[current] = {}
            continue
        if "=" not in line:
            raise ValueError(f"bad kv line (no '='): {raw}")
        if current is None:
            raise ValueError(f"kv line before section header: {raw}")
        k, v = line.split("=", 1)
        out[current][k.strip()] = v.strip()

    return out


@dataclass(frozen=True)
class SoaResult:
    host: str
    host_short: str
    legs_path: str
    yaml_path: str
    hash_spec_id: str
    hash_algo: str

    leg_home_fs: str
    leg_repo_fs: str
    leg_user: str

    duople_home_repo: str
    duople_home_user: str
    duople_repo_user: str

    stool_full: str
    stool_show: str

    expected_stool_full: Optional[str]
    ok: bool


class SoaHasher:
    def compute_from_legs_text(self, legs_text: str) -> Tuple[str, str, str, str, str, str, str]:
        parsed = parse_legs_kv(legs_text)

        # required legs
        home_fs = parsed.get("leg.home_fs", {})
        repo_fs = parsed.get("leg.repo_fs", {})
        user = parsed.get("leg.user", {})

        # ensure null semantics for missing common keys (do not omit)
        for key in ("partuuid",):
            if key not in home_fs:
                home_fs[key] = "null"
            if key not in repo_fs:
                repo_fs[key] = "null"

        h_home = _leg_hash(home_fs)
        h_repo = _leg_hash(repo_fs)
        h_user = _leg_hash(user)

        d_hr = _duople(h_home, h_repo)
        d_hu = _duople(h_home, h_user)
        d_ru = _duople(h_repo, h_user)

        stool = _stool(d_hr, d_hu, d_ru)

        return h_home, h_repo, h_user, d_hr, d_hu, d_ru, stool


def verify_current_host(
    home: Path = Path.home(),
    now_hostf: Optional[str] = None,
) -> SoaResult:
    # host
    hostf = now_hostf or socket.getfqdn()
    hs = _host_short(hostf)

    legs_path = home / ".hee" / "current" / "soa" / f"{hs}.legs.kv"
    yaml_path = home / ".hee" / "index" / "_.yaml"

    legs_text = _read_text(legs_path)
    yaml_text = _read_text(yaml_path)

    expected = _parse_expected_stool_from_yaml(yaml_text)

    hasher = SoaHasher()
    h_home, h_repo, h_user, d_hr, d_hu, d_ru, stool = hasher.compute_from_legs_text(legs_text)

    ok = (expected == stool) if expected else False

    return SoaResult(
        host=hostf,
        host_short=hs,
        legs_path=str(legs_path),
        yaml_path=str(yaml_path),
        hash_spec_id=HASH_SPEC_ID,
        hash_algo=HASH_ALGO,

        leg_home_fs=h_home,
        leg_repo_fs=h_repo,
        leg_user=h_user,

        duople_home_repo=d_hr,
        duople_home_user=d_hu,
        duople_repo_user=d_ru,

        stool_full=stool,
        stool_show=_show(stool),

        expected_stool_full=expected,
        ok=ok,
    )
