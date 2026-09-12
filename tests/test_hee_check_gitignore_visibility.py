"""hee check gitignore knows a private repo is private inside GitHub Actions, and
hee check all runs it.

Measured 2026-09-11: no org CI job gives gh a token, so the check read every
repo as public in CI. fleet-ops tracks sealed ciphertext on purpose, and its
re-include would have failed fleet-ops' own CI as CRITICAL the day gitignore
joined `all`. The Actions event payload names the repository and its
visibility, so the check reads it when gh cannot answer -- and only when the
payload names the repository being checked.

Hermetic: a stub gh that always fails stands in for the real one."""
import json, os, subprocess, tempfile, unittest
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1] / "tooling" / "bin" / "hee-check"


class Visibility(unittest.TestCase):
    def run_check(self, event=None, sub="gitignore"):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            bin_ = d / "bin"; bin_.mkdir()
            (bin_ / "gh").write_text("#!/bin/sh\nexit 1\n"); (bin_ / "gh").chmod(0o755)
            repo = d / "repo"; repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", "https://github.com/example-owner/example-repo.git"], check=True)
            (d / "base.gitignore").write_text("cache/\n")
            (repo / ".gitignore").write_text("cache/\n!cache/keys.gpg\n")
            env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}", HEE_GITIGNORE_BASE=str(d / "base.gitignore"))
            env.pop("GITHUB_EVENT_PATH", None)
            if event is not None:
                (d / "event.json").write_text(json.dumps(event)); env["GITHUB_EVENT_PATH"] = str(d / "event.json")
            r = subprocess.run([str(CHECK), sub, str(repo)], capture_output=True, text=True, env=env)
            return r.returncode, r.stdout + r.stderr

    def test_no_answer_means_public_and_critical(self):
        rc, out = self.run_check()
        self.assertEqual(rc, 2, out)
        self.assertIn("negation re-includes a secret path: !cache/keys.gpg", out)

    def test_event_payload_for_this_repo_says_private(self):
        rc, out = self.run_check({"repository": {"full_name": "Example-Owner/example-repo", "visibility": "private", "private": True}})
        self.assertEqual(rc, 1, out)
        self.assertIn("(private, may be deliberate)", out)

    def test_event_payload_for_another_repo_is_ignored(self):
        rc, out = self.run_check({"repository": {"full_name": "example-owner/other-repo", "visibility": "private"}})
        self.assertEqual(rc, 2, out)

    def test_all_runs_gitignore(self):
        rc, out = self.run_check(sub="all")
        self.assertIn("negation re-includes a secret path", out)
        self.assertEqual(rc, 2, out)


if __name__ == "__main__":
    unittest.main()
