"""hee-check examples: every '# ci' example in every tool's --help runs clean.

This is the unit test the man pages carry built in (operator, 2026-09-11:
"ci must use the man pages to ensure they work, unit tests builtin"). A
tool whose marked example breaks fails this test, and `hee check all` on
this repo, the same way.
"""
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tooling" / "bin" / "hee-check"


class Examples(unittest.TestCase):
    def test_marked_examples_run_clean(self):
        r = subprocess.run([str(CHECK), "examples", str(ROOT)], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        m = re.search(r"(\d+) example\(s\) from (\d+) tool\(s\) ran clean", r.stdout)
        self.assertIsNotNone(m, r.stdout)
        self.assertGreaterEqual(int(m.group(1)), 5, "fewer marked examples than the tools this test knows about")

    def test_extractor_sees_the_marker_and_nothing_else(self):
        # A fake tool whose --help carries one marked and one unmarked example:
        # only the marked one runs, and a failing marked one is CRITICAL.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "tooling" / "bin").mkdir(parents=True)
            (root / "tooling" / "bin" / "hee").write_text("#!/bin/sh\nexit 0\n"); os.chmod(root / "tooling" / "bin" / "hee", 0o755)
            good = root / "tooling" / "bin" / "hee-good"
            good.write_text('#!/bin/sh\ncase "$1" in --help) printf "EXAMPLES\\n  $ true   # ci\\n  $ false\\n";; esac\n'); os.chmod(good, 0o755)
            r = subprocess.run([str(CHECK), "examples", str(root)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("1 example(s) from 1 tool(s)", r.stdout)
            bad = root / "tooling" / "bin" / "hee-bad"
            bad.write_text('#!/bin/sh\ncase "$1" in --help) printf "EXAMPLES\\n  $ false   # ci\\n";; esac\n'); os.chmod(bad, 0o755)
            r = subprocess.run([str(CHECK), "examples", str(root)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("hee-bad example exited 1", r.stdout)


if __name__ == "__main__":
    unittest.main()
