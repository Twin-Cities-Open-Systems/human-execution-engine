"""hee check gitignore --fix puts the managed base block FIRST.

A .gitignore's last matching rule wins, so a repo's own rules must come after
the base to be able to narrow it. Appended at the end, the base's bare
`secrets/` re-excluded fleet-ops' `!.hee/secrets/` re-include and made every
sealed credential unaddable (measured 2026-09-11).

The test uses neutral patterns: a throwaway repo has no GitHub origin, so the
tool treats it as public, and in a public repo --fix deliberately deletes any
negation that re-includes a secret path. Ordering is what is under test here.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tooling" / "bin" / "hee-check"


class BaseBlockOrder(unittest.TestCase):
    def test_fix_writes_the_block_first_so_later_repo_rules_win(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"; repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            base = Path(d) / "base.gitignore"
            base.write_text("cache/\n*.log\n")
            (repo / ".gitignore").write_text("!cache/\ncache/*\n!cache/*.keep\n")
            env = dict(os.environ, HEE_GITIGNORE_BASE=str(base))
            subprocess.run([str(CHECK), "gitignore", "--fix", str(repo)], capture_output=True, text=True, env=env)
            text = (repo / ".gitignore").read_text()
            self.assertTrue(text.startswith("# >>> hee gitignore base >>>"), text)
            self.assertLess(text.index("# <<< hee gitignore base <<<"), text.index("!cache/"))

            def ignored(p):
                return subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", "--no-index", p]).returncode == 0
            self.assertFalse(ignored("cache/data.keep"), "the repo's later re-include must win over the base")
            self.assertTrue(ignored("cache/data.tmp"), "the repo's narrowing still applies")
            self.assertTrue(ignored("app.log"), "the base still applies")

    def test_second_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"; repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            base = Path(d) / "base.gitignore"
            base.write_text("cache/\n*.log\n")
            (repo / ".gitignore").write_text("!cache/\n")
            env = dict(os.environ, HEE_GITIGNORE_BASE=str(base))
            for _ in range(2):
                subprocess.run([str(CHECK), "gitignore", "--fix", str(repo)], capture_output=True, text=True, env=env)
            base.write_text("cache/\n*.log\nnew-pattern\n")   # the base grows: the block is rewritten, still first
            subprocess.run([str(CHECK), "gitignore", "--fix", str(repo)], capture_output=True, text=True, env=env)
            text = (repo / ".gitignore").read_text()
            self.assertEqual(text.count("# >>> hee gitignore base >>>"), 1)
            self.assertTrue(text.startswith("# >>> hee gitignore base >>>"))
            self.assertIn("new-pattern", text)
            self.assertLess(text.index("new-pattern"), text.index("!cache/"))


if __name__ == "__main__":
    unittest.main()
