"""The repo declares its check exemptions once, in .hee/config.yaml, and a
local run reads the same list CI does.

Real trigger, fleet-ops ticket 0067 (2026-09-18): HEE_REFS_SKIP and
HEE_HOME_PATH_SKIP lived only in the CI workflow's env, so `hee check all`
was green on GitHub and red on every laptop for the same tree.

Also covers the two sibling-resolution faults measured the same day: a
second clone of one repository made every cross-repo reference ambiguous,
and a worktree found no siblings at all.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tooling" / "bin" / "hee-check"
LINT = ROOT / "tooling" / "bin" / "hee-lint"


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def make_repo(path: Path, files: dict[str, str], origin: str | None = None):
    path.mkdir(parents=True)
    git("init", "-q", str(path), cwd=path)
    git("config", "user.email", "t@example.invalid", cwd=path)
    git("config", "user.name", "t", cwd=path)
    for rel, text in files.items():
        f = path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    if origin:
        git("remote", "add", "origin", origin, cwd=path)
    git("add", "-A", cwd=path)
    git("commit", "-q", "-m", "init", cwd=path)


def run(tool, *args, cwd, env=None):
    e = dict(os.environ, HEE_STATUS_STYLE="plain")
    e.pop("HEE_REFS_SKIP", None); e.pop("HEE_HOME_PATH_SKIP", None); e.pop("HEE_LINT_SKIP", None)
    if env:
        e.update(env)
    r = subprocess.run([str(tool), *args], cwd=cwd, capture_output=True, text=True, env=e, check=False)
    return r.returncode, r.stdout + r.stderr


class RepoConfig(unittest.TestCase):
    def test_refs_skip_from_config(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            make_repo(repo, {
                "docs/a.md": "see `docs/missing.md`\n",
                "rendered/copy.md": "see `docs/missing.md`\n",
                ".hee/config.yaml": "check:\n  refs_skip:\n    - rendered\n",
            })
            rc, out = run(CHECK, "refs", ".", cwd=repo)
            self.assertEqual(rc, 2, out)
            self.assertIn("docs/a.md:1", out)
            self.assertNotIn("rendered/copy.md", out, "check.refs_skip was not read")

    def test_env_appends_to_config(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            make_repo(repo, {
                "docs/a.md": "see `docs/missing.md`\n",
                "rendered/copy.md": "see `docs/missing.md`\n",
                ".hee/config.yaml": "check:\n  refs_skip:\n    - rendered\n",
            })
            rc, out = run(CHECK, "refs", ".", cwd=repo, env={"HEE_REFS_SKIP": "docs"})
            self.assertEqual(rc, 0, out)

    def test_home_path_skip_from_config(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            make_repo(repo, {
                "bin/real.sh": "#!/bin/sh\ncat /home/someone/x\n",
                "jobs/j1/in/snap.sh": "#!/bin/sh\ncat /home/agent/jobs/x\n",
                ".hee/config.yaml": "check:\n  home_path_skip:\n    - ':!jobs/*/in/*'\n",
            })
            rc, out = run(CHECK, "boundary", ".", cwd=repo)
            self.assertEqual(rc, 2, out)
            self.assertIn("bin/real.sh", out)
            self.assertNotIn("jobs/j1/in/snap.sh", out, "check.home_path_skip was not read")

    def test_lint_skip_from_config(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            bad = "apiVersion: hee/v1\nkind: Nope\n"
            make_repo(repo, {
                "hee/x.yaml": bad,
                "public/x.yaml": bad,
                ".hee/config.yaml": "check:\n  lint_skip:\n    - ':!public/*'\n",
            })
            _rc, out = run(LINT, cwd=repo)
            self.assertIn("hee/x.yaml", out)
            self.assertNotIn("public/x.yaml", out, "check.lint_skip was not read")

    def test_other_top_level_keys_do_not_leak(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            make_repo(repo, {
                "rendered/copy.md": "see `docs/missing.md`\n",
                "docs/keep.md": "ok\n",
                ".hee/config.yaml": "dispatch:\n  refs_skip:\n    - rendered\ncheck:\n  lint_skip:\n    - ':!x'\n",
            })
            rc, out = run(CHECK, "refs", ".", cwd=repo)
            self.assertEqual(rc, 2, "a list under another key was read as check.refs_skip: " + out)


class Siblings(unittest.TestCase):
    def test_duplicate_clone_is_one_answer(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            make_repo(base / "consumer", {"docs/a.md": "see `doctrine/rule.md`\n", "doctrine/local.md": "x\n"},
                      origin="git@github.com:org/consumer.git")
            make_repo(base / "doctrine-a", {"doctrine/rule.md": "x\n"},
                      origin="git@github.com:org/doctrine.git")
            make_repo(base / "Doctrine-B", {"doctrine/rule.md": "x\n"},
                      origin="https://github.com/org/doctrine")
            rc, out = run(CHECK, "refs", ".", cwd=base / "consumer")
            self.assertEqual(rc, 0, out)
            self.assertIn("cross-repo references resolved", out)

    def test_two_different_repos_stay_ambiguous(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            make_repo(base / "consumer", {"docs/a.md": "see `doctrine/rule.md`\n", "doctrine/local.md": "x\n"},
                      origin="git@github.com:org/consumer.git")
            make_repo(base / "one", {"doctrine/rule.md": "x\n"}, origin="git@github.com:org/one.git")
            make_repo(base / "two", {"doctrine/rule.md": "x\n"}, origin="git@github.com:org/two.git")
            rc, out = run(CHECK, "refs", ".", cwd=base / "consumer")
            self.assertEqual(rc, 2, out)

    def test_own_second_clone_is_not_a_sibling(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            make_repo(base / "consumer", {"docs/a.md": "see `docs/later.md`\n"},
                      origin="git@github.com:org/consumer.git")
            make_repo(base / "consumer-2", {"docs/later.md": "x\n"},
                      origin="git@github.com:org/consumer.git")
            rc, out = run(CHECK, "refs", ".", cwd=base / "consumer")
            self.assertEqual(rc, 2, "resolved against another clone of itself: " + out)

    def test_worktree_uses_main_checkouts_siblings(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            make_repo(base / "consumer", {"docs/a.md": "see `doctrine/rule.md`\n", "doctrine/local.md": "x\n"},
                      origin="git@github.com:org/consumer.git")
            make_repo(base / "doctrine", {"doctrine/rule.md": "x\n"},
                      origin="git@github.com:org/doctrine.git")
            wt = base / "consumer.worktrees" / "feature"
            git("worktree", "add", "-q", "-b", "feature", str(wt), cwd=base / "consumer")
            rc, out = run(CHECK, "refs", ".", cwd=wt)
            self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
