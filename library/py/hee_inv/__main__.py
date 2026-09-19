"""python3 -m hee_inv add --json FILE [--dataset DIR | --tcos-repo PATH] [--kind asset|stock] [--dry-run]

Called by tooling/bin/hee-inv, which owns the help text. stdout is the
record path (or, with --dry-run, the record); status lines go to stderr.
"""
import os
import sys
from pathlib import Path

from hee_status import ArgumentParser, Status, emit, exit_with

from hee_inv import Invalid, Unusable, add


def main() -> Status:
    ap = ArgumentParser(prog="hee inv add")
    ap.add_argument("cmd", choices=["add"])
    ap.add_argument("--json", required=True, metavar="FILE", help="the request document, or - for stdin")
    ap.add_argument("--tcos-repo", default=None)
    ap.add_argument("--dataset", metavar="DIR", default=None, help="a store's dataset directory; not a git repo")
    ap.add_argument("--kind", choices=["asset", "stock"], default="asset")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.dataset and a.tcos_repo:
        return emit(Status.UNKNOWN, "--dataset and --tcos-repo are mutually exclusive")
    if a.kind == "stock" and not a.dataset:
        return emit(Status.UNKNOWN, "stock records live in datasets, not a --tcos-repo: pass --dataset DIR")
    if not a.dataset:
        a.tcos_repo = a.tcos_repo or os.environ.get("TCOS_REPO", str(Path.home() / "git" / "tcos-plan-private"))
    try:
        data = sys.stdin.buffer.read() if a.json == "-" else Path(a.json).read_bytes()
    except OSError as e:
        return emit(Status.UNKNOWN, f"cannot read {a.json}: {e.strerror}")
    try:
        if a.dataset:
            rel, text = add(data, dataset=Path(a.dataset), dry_run=a.dry_run, kind=a.kind)
        else:
            rel, text = add(data, Path(a.tcos_repo), dry_run=a.dry_run, kind=a.kind)
    except Invalid as e:
        return emit(Status.CRITICAL, str(e))
    except Unusable as e:
        return emit(Status.UNKNOWN, str(e))
    if a.dry_run:
        sys.stdout.write(text)
        emit(Status.OK, f"dry run: would write {rel}", stream=sys.stderr)
    else:
        print(rel)
        emit(Status.OK, f"wrote {rel}", stream=sys.stderr)
    return Status.OK


if __name__ == "__main__":
    exit_with(main)
