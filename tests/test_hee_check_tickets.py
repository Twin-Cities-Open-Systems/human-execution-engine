"""hee check tickets: CRITICAL on a broken record, advisory WARNING on a move with no why."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tooling" / "bin" / "hee-check"
FIXTURE = ROOT / "tests" / "fixtures" / "tickets-workspace" / "demo" / ".hee" / "tickets"


class Tickets(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", str(self.d)], check=True)
        shutil.copytree(FIXTURE, self.d / ".hee" / "tickets")

    def tearDown(self):
        shutil.rmtree(self.d)

    def check(self):
        return subprocess.run([str(CHECK), "tickets", str(self.d)], capture_output=True, text=True)

    def test_warning_is_not_critical(self):
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("1 move(s) record no why", r.stdout + r.stderr)

    def test_unreadable_and_illegal_are_critical(self):
        (self.d / ".hee" / "tickets" / "0003.yaml").write_text("id: '0003'\ndescription: 'resume's guide'\n")
        (self.d / ".hee" / "tickets" / "0004.yaml").write_text(
            "id: '0004'\ncreated_at: a\ndescription: skipped footgun\nstatus: open\nstage: dogfood\n"
            "stage_history:\n- stage: idea\n  at: a\n- stage: dogfood\n  at: b\n  why: w\n")
        r = self.check()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        out = r.stdout + r.stderr
        self.assertIn("/0003: UNREADABLE", out)
        self.assertIn("illegal move idea -> dogfood", out)

    def test_no_tickets_is_ok(self):
        shutil.rmtree(self.d / ".hee")
        self.assertEqual(self.check().returncode, 0)


if __name__ == "__main__":
    unittest.main()
