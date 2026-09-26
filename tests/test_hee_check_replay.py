"""hee-check replays a repo's OWN declared exemptions when unset locally.

The bug: `hee check all` in fleet-ops reported CRITICAL refs under
pve/agents/jobs that the repo's CI never sees, because CI sets HEE_REFS_SKIP
in the workflow env and a local run got nothing. The exemption is a property
of the repo; the checker now reads it from the repo's .github/workflows when
the caller has not set it. An explicit value (even empty) is left alone.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tooling" / "bin" / "hee-check"


def _mk_repo(d, refs_skip=None):
    r = Path(d)
    (r / ".github" / "workflows").mkdir(parents=True)
    (r / "docs").mkdir()
    (r / "docs" / "real.md").write_text("real\n")
    (r / "jobs").mkdir()
    # A doc under jobs/ referencing a docs/ file that does NOT exist: a broken
    # ref (docs is a real top-level dir, so the token counts as a reference).
    (r / "jobs" / "note.md").write_text("see `docs/missing.md`\n")
    if refs_skip is not None:
        (r / ".github" / "workflows" / "ci.yml").write_text(
            "jobs:\n  x:\n    env:\n"
            f'      HEE_REFS_SKIP: "{refs_skip}"\n'
        )
    else:
        (r / ".github" / "workflows" / "ci.yml").write_text("jobs:\n  x:\n    steps: []\n")
    subprocess.run(["git", "init", "-q", str(r)], check=True)
    # hee_refs enumerates via `git ls-files`, so the files must be tracked.
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
    return r


def _refs(r, env_extra=None):
    env = dict(os.environ)
    env["HEE_STATUS_STYLE"] = "plain"
    env.pop("HEE_REFS_SKIP", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([str(CHECK), "refs", str(r)], capture_output=True, text=True, env=env)


class Replay(unittest.TestCase):
    def test_broken_ref_is_critical_without_exemption(self):
        with tempfile.TemporaryDirectory() as d:
            r = _mk_repo(d, refs_skip=None)
            out = _refs(r)
            self.assertIn("CRITICAL", out.stdout, out.stdout)
            self.assertIn("docs/missing.md", out.stdout)

    def test_repo_declared_skip_is_replayed_when_unset(self):
        with tempfile.TemporaryDirectory() as d:
            r = _mk_repo(d, refs_skip="jobs")
            out = _refs(r)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertIn("replaying exemptions", out.stdout)
            self.assertNotIn("CRITICAL", out.stdout)

    def test_explicit_empty_skip_is_honored_not_overridden(self):
        # Caller sets HEE_REFS_SKIP="" deliberately -- the repo's own skip must
        # NOT be replayed over it, so the broken ref is still reported.
        with tempfile.TemporaryDirectory() as d:
            r = _mk_repo(d, refs_skip="jobs")
            out = _refs(r, env_extra={"HEE_REFS_SKIP": ""})
            self.assertIn("CRITICAL", out.stdout, out.stdout)
            self.assertNotIn("replaying exemptions", out.stdout)


if __name__ == "__main__":
    unittest.main()
