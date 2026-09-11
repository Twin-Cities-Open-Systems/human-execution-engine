"""hee check gitignore --fix names its base without an absolute path.

Real trigger, 2026-09-11: the managed block wrote `# Base: /home/<user>/git/.github/gitignore/base.gitignore`
into this repo's .gitignore and into 17 org repos' PRs. A local home path in a
shared file is exactly what rule 10 forbids, and it tells every reader how one
machine is laid out."""
import os, subprocess, tempfile, unittest
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1] / "tooling" / "bin" / "hee-check"


def fixed_block(base_path):
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d) / "repo"; repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        base = Path(d) / base_path; base.parent.mkdir(parents=True, exist_ok=True); base.write_text("cache/\n*.log\n")
        (repo / ".gitignore").write_text("build/\n")
        env = dict(os.environ, HEE_GITIGNORE_BASE=str(base))
        subprocess.run([str(CHECK), "gitignore", "--fix", str(repo)], capture_output=True, text=True, env=env)
        return (repo / ".gitignore").read_text(), d


class BaseLabel(unittest.TestCase):
    def test_org_base_is_named_by_its_org_path(self):
        text, d = fixed_block(".github/gitignore/base.gitignore")
        self.assertIn("# Base: .github/gitignore/base.gitignore (the org baseline)\n", text)
        self.assertNotIn(d, text)

    def test_any_other_base_is_named_by_basename_only(self):
        text, d = fixed_block("elsewhere/my.base")
        self.assertIn("# Base: my.base (from HEE_GITIGNORE_BASE)\n", text)
        self.assertNotIn(d, text)
        self.assertNotIn("/home/", text)


if __name__ == "__main__":
    unittest.main()
