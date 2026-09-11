"""hee view --tickets: tickets joined to agent jobs and their blockers, offline."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "tooling" / "bin" / "hee-view"


class Feed(unittest.TestCase):
    def test_blocked_and_dispatched_jobs(self):
        r = subprocess.run([sys.executable, str(VIEW), "--tickets", "--json", "--offline",
                            "--root", "tests/fixtures/dispatch", "--workspace", "tests/fixtures/tickets-workspace"],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        doc = json.loads(r.stdout)
        jobs = {j["name"]: j for j in doc["jobs"]}
        self.assertEqual(jobs["demo"]["state"], "dispatched")
        self.assertEqual(jobs["demo"]["runs"], 1)
        self.assertEqual(jobs["demo-blocked"]["state"], "blocked")
        self.assertEqual(jobs["demo-blocked"]["open_blockers"], ["demo/0001"])
        blocks = {t["key"]: t.get("blocks") for t in doc["tickets"]}
        self.assertEqual(sorted(blocks["demo/0001"]), ["demo-blocked", "ticket:demo/0003"])
        self.assertEqual({t["key"]: t.get("open_blockers") for t in doc["tickets"]}["demo/0003"], ["demo/0001"])
        self.assertEqual(doc["prs"], [])
        self.assertTrue(doc["offline"])


if __name__ == "__main__":
    unittest.main()
