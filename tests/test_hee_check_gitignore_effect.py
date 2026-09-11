"""hee check gitignore judges the baseline by what git ignores, not by text.

Real trigger, 2026-09-11. The check matched each baseline line exactly, so it
called a repo with an equivalent pattern uncovered and passed a repo whose
baseline line a later rule overrode. On the operator's machine, 18 local clones
also carried `.hee/` in .git/info/exclude, written by hee-attach, which hid
paths that CI's fresh clones would stage.

Neutral patterns throughout: a throwaway repo has no origin, so the tool treats
it as public, and the negation danger list is not what is under test.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tooling" / "bin" / "hee-check"


def run(gitignore, base="cache/\n*.log\n", info_exclude=None):
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d) / "repo"; repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        (Path(d) / "base.gitignore").write_text(base)
        (repo / ".gitignore").write_text(gitignore)
        if info_exclude is not None:
            (repo / ".git" / "info").mkdir(parents=True, exist_ok=True)
            (repo / ".git" / "info" / "exclude").write_text(info_exclude)
        env = dict(os.environ, HEE_GITIGNORE_BASE=str(Path(d) / "base.gitignore"))
        r = subprocess.run([str(CHECK), "gitignore", str(repo)], capture_output=True, text=True, env=env)
        return r.returncode, r.stdout + r.stderr


class ByEffect(unittest.TestCase):
    def test_equivalent_pattern_counts_as_covered(self):
        rc, out = run("**/cache/\nlogs-and-more/\n*.log\n")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("not excluded", out)

    def test_present_line_overridden_later_is_not_covered(self):
        rc, out = run("cache/\n*.log\n!cache/\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("1 baseline secret path(s) not excluded", out)
        self.assertIn("not ignored: cache/", out)

    def test_local_info_exclude_cannot_hide_the_gap(self):
        rc, out = run("*.log\n", info_exclude="cache/\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("not ignored: cache/", out)

    def test_root_anchored_pattern_misses_deeper_paths(self):
        rc, out = run("/cache/\n*.log\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("deep/cache/k", out)

    def test_samples(self):
        r = subprocess.run(["sh", "-c", ". /dev/stdin; for p in 'secrets/' '.hee/secrets/' '*.env' '.netrc' '/top/'; do _gitignore_samples \"$p\"; done"],
                           input=subprocess.run(["sed", "-n", "/^_gitignore_samples() {/,/^}/p", str(CHECK)], capture_output=True, text=True).stdout,
                           capture_output=True, text=True)
        self.assertEqual(r.stdout.split(), ["secrets/k", "deep/secrets/k", ".hee/secrets/k", "sample.env", "deep/sample.env", ".netrc", "deep/.netrc", "top/k"])


if __name__ == "__main__":
    unittest.main()
