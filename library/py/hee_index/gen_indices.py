#!/usr/bin/env python3
import hashlib, json, pathlib, subprocess
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parents[3]  # repo root
def sh(*args: str) -> str:
    return subprocess.check_output(args, cwd=REPO, text=True).strip()

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def gh_owner_repo() -> str:
    return sh("gh","repo","view","--json","nameWithOwner","-q",".nameWithOwner")

def head_sha() -> str:
    return sh("git","rev-parse","HEAD")

def mk_gh_raw(owner_repo: str, ref: str, path: str) -> str:
    # ref should be "refs/heads/main" or a commit sha; we’ll use commit sha for immutability
    if ref.startswith("refs/"):
        return f"https://raw.githubusercontent.com/{owner_repo}/{ref}/{path}"
    return f"https://raw.githubusercontent.com/{owner_repo}/{ref}/{path}"

def list_files() -> list[str]:
    # tracked files only
    out = sh("git","ls-files")
    files = [line for line in out.splitlines() if line.strip()]
    files.sort(key=lambda s: s.encode("utf-8"))
    return files

def build_repo_files_index(owner_repo: str, ref: str) -> dict:
    files = list_files()
    recs = []
    agg_lines = ["sqz-token-hash.v1\n"]
    for p in files:
        fp = REPO / p
        b = fp.read_bytes()
        h = sha256_bytes(b)
        recs.append({
            "path": p,
            "size": fp.stat().st_size,
            "sha256": h,
            "gh_raw": mk_gh_raw(owner_repo, ref, p),
        })
        agg_lines.append(p + "\n" + h + "\n")
    agg = sha256_bytes("".join(agg_lines).encode("utf-8"))
    token = agg[:16]
    return {
        "version": "repo-files.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "repo": {"owner_repo": owner_repo, "ref": ref, "head_sha": head_sha()},
        "hash_policy": {"name": "sqz-token-hash.v1", "aggregate_sha256": agg, "token": token},
        "files": recs,
    }

def build_canon_index(owner_repo: str, ref: str) -> dict:
    canon = [
        {"kind":"Contract","path":"pills/contracts/pr-handoff.v1.yaml"},
        {"kind":"Contract","path":"pills/contracts/evidence-index.v1.yaml"},
        {"kind":"Schema","path":"schemas/hee/v1/hee-object.schema.json"},
        {"kind":"Schema","path":"schemas/hee/v1/evidence-pointer.schema.json"},
    ]
    for c in canon:
        c["gh_raw"] = mk_gh_raw(owner_repo, ref, c["path"])
    return {
        "version": "canon-index.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "repo": {"owner_repo": owner_repo, "ref": ref, "head_sha": head_sha()},
        "canon": canon,
    }

def main() -> int:
    owner_repo = gh_owner_repo()
    # immutable ref (commit sha) so URLs never drift
    ref = head_sha()
    outdir = REPO / "hee" / "evidence" / "index"
    outdir.mkdir(parents=True, exist_ok=True)

    canon = build_canon_index(owner_repo, ref)
    repo_idx = build_repo_files_index(owner_repo, ref)

    (outdir / "canon.index.v1.json").write_text(json.dumps(canon, indent=2, sort_keys=True) + "\n")
    (outdir / "repo.files.v1.json").write_text(json.dumps(repo_idx, indent=2, sort_keys=True) + "\n")
    print(str(outdir))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
