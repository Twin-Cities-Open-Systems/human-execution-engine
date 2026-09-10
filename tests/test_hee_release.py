"""hee-release: -lab runs the card's build before any surface's lab command."""
import os, subprocess, sys, tempfile, unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tooling" / "bin" / "hee-release"


class LabBuildsFirst(unittest.TestCase):
    def test_lab_builds_before_surfaces(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"; repo.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            (repo / "release.card.v1.yaml").write_text(
                "apiVersion: hee/v1\nkind: Card\nmetadata: { name: t-release, labels: { domain: release } }\n"
                "spec:\n  build: \"echo built > built.txt\"\n  outputs: [\"built.txt\"]\n"
                "  surfaces:\n    - { name: t, lab: \"test -f built.txt && echo lab-saw-build > lab.txt\", promote: \"true\" }\n")
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"], cwd=repo, check=True)
            r = subprocess.run([sys.executable, str(TOOL), "-lab"], cwd=repo, capture_output=True, text=True, env=dict(os.environ, HOME=d))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((repo / "built.txt").exists(), "build did not run")
            self.assertEqual((repo / "lab.txt").read_text().strip(), "lab-saw-build", "lab ran before build")


if __name__ == "__main__":
    unittest.main()
