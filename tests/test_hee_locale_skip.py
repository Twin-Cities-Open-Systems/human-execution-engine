"""hee check locale honors HEE_LOCALE_SKIP, so a repo can exempt paths it did
not author (e.g. fleet-ops' pve/agents/jobs/** -- copies shipped to and from
agents). Same declare-in-CI shape as HEE_REFS_SKIP; a real en_GB spelling
outside the skip must still be reported.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tooling" / "bin" / "hee-check"


def _mk(d):
    r = Path(d)
    (r / "jobs" / "in").mkdir(parents=True)
    # An agent job artifact this repo did not author: an en_GB word.
    (r / "jobs" / "in" / "artifact.md").write_text("The tool's behaviour differs.\n")
    # Authored prose with an en_GB word.
    (r / "notes.md").write_text("The colour must be right.\n")
    subprocess.run(["git", "init", "-q", str(r)], check=True)
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
    return r


def _locale(r, skip=None):
    env = dict(os.environ, HEE_STATUS_STYLE="plain")
    if skip is not None:
        env["HEE_LOCALE_SKIP"] = skip
    else:
        env.pop("HEE_LOCALE_SKIP", None)
    r = subprocess.run([str(CHECK), "locale", str(r)], capture_output=True, text=True, env=env)
    # emit() writes findings to stderr; callers grep the combined stream.
    r.out = r.stdout + r.stderr
    return r


class LocaleSkip(unittest.TestCase):
    def test_without_skip_both_are_reported(self):
        with tempfile.TemporaryDirectory() as d:
            r = _mk(d)
            out = _locale(r)
            self.assertIn("notes.md", out.out)
            self.assertIn("jobs/in/artifact.md", out.out)

    def test_skip_exempts_the_job_path_only(self):
        with tempfile.TemporaryDirectory() as d:
            r = _mk(d)
            out = _locale(r, skip="jobs")
            # The exempted artifact is gone; the authored file still reported.
            self.assertNotIn("jobs/in/artifact.md", out.out)
            self.assertIn("notes.md", out.out)


if __name__ == "__main__":
    unittest.main()
