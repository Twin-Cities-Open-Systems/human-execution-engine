"""hee-ticket: idea->footgun<->dogfood with evidence, -json, unreadable records.

Operator, 2026-09-11: "let's make sure they get correctly processesed through
idea->footgun<->dogfood". Before this the tool only moved forward, recorded no
evidence, and listed an unreadable ticket as an ordinary open one with exit 0.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tooling" / "bin" / "hee-ticket"
FIXTURE = ROOT / "tests" / "fixtures" / "tickets-workspace"


def run(args, cwd):
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=cwd, capture_output=True, text=True)


class Repo(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.repo = Path(self.d) / "demo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.assertEqual(run(["-new", "try a thing"], self.repo).returncode, 0)

    def tearDown(self):
        shutil.rmtree(self.d)

    def ticket(self):
        import yaml
        return yaml.safe_load((self.repo / ".hee" / "tickets" / "0001.yaml").read_text())

    def test_advance_records_why_and_stops_at_dogfood(self):
        self.assertEqual(run(["-advance", "1", "--why", "it can drop records"], self.repo).returncode, 0)
        self.assertEqual(run(["-advance", "1", "--why", "ran it for a day"], self.repo).returncode, 0)
        r = run(["-advance", "1"], self.repo)
        self.assertEqual(r.returncode, 0)
        self.assertIn("-back", r.stdout)
        t = self.ticket()
        self.assertEqual(t["stage"], "dogfood")
        self.assertEqual([h.get("why") for h in t["stage_history"]], [None, "it can drop records", "ran it for a day"])
        self.assertEqual(t["id"], "0001")

    def test_back_only_from_dogfood_and_only_with_why(self):
        r = run(["-back", "1", "--why", "x"], self.repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("only a dogfood ticket", r.stderr)
        run(["-advance", "1", "--why", "a"], self.repo)
        run(["-advance", "1", "--why", "b"], self.repo)
        self.assertNotEqual(run(["-back", "1"], self.repo).returncode, 0)
        r = run(["-back", "1", "--why", "real use found a footgun"], self.repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        t = self.ticket()
        self.assertEqual(t["stage"], "footgun")
        self.assertEqual(t["stage_history"][-1]["why"], "real use found a footgun")

    def test_unreadable_ticket_is_critical_in_list_and_json(self):
        (self.repo / ".hee" / "tickets" / "0002.yaml").write_text("id: '0002'\ndescription: 'it's broken'\n  bad: [\n")
        r = run(["-list"], self.repo)
        self.assertEqual(r.returncode, 2)
        self.assertIn("CRITICAL", r.stderr)
        doc = json.loads(run(["-json"], self.repo).stdout)
        bad = [t for t in doc["tickets"] if t["id"] == "0002"][0]
        self.assertEqual(bad["flow"][0]["severity"], "CRITICAL")


class Json(unittest.TestCase):
    def test_fixture_workspace_flow_and_octal_id(self):
        r = run(["-json", "--workspace", str(FIXTURE)], ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        doc = json.loads(r.stdout)
        keys = {t["key"]: t for t in doc["tickets"]}
        self.assertIn("demo/0010", keys, "an unquoted 0010 must stay 0010, not the octal 8")
        self.assertEqual(doc["transitions"]["dogfood"], ["footgun"])
        self.assertEqual(keys["demo/0001"]["flow"], [])
        self.assertEqual([f["severity"] for f in keys["demo/0002"]["flow"]], ["WARNING"])

    def test_findings_for_illegal_moves(self):
        import importlib.machinery
        import importlib.util
        loader = importlib.machinery.SourceFileLoader("hee_ticket_ut", str(TOOL))
        spec = importlib.util.spec_from_loader("hee_ticket_ut", loader)
        m = importlib.util.module_from_spec(spec)
        loader.exec_module(m)
        rec = {"stage": "idea", "status": "open", "stage_history": [
            {"stage": "idea", "at": "a"}, {"stage": "dogfood", "at": "b", "why": "w"}, {"stage": "idea", "at": "c", "why": "w"}]}
        what = [f["what"] for f in m.flow_findings(rec) if f["severity"] == "CRITICAL"]
        self.assertTrue(any("idea -> dogfood" in w for w in what), what)
        self.assertTrue(any("dogfood -> idea" in w for w in what), what)


class ListOne(unittest.TestCase):
    """-list SPEC prints whole records (operator, 2026-09-11: `hee ticket -list 0102`)."""

    def test_one_ticket_whole_record_with_whys(self):
        r = run(["-list", "demo/0002", "--workspace", str(FIXTURE)], ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("# demo/0002", r.stdout)
        self.assertIn("why: ran against every repo for a day", r.stdout)
        self.assertNotIn("demo/0001", r.stdout)

    def test_range_and_no_match(self):
        r = run(["-list", "1-2", "--workspace", str(FIXTURE)], ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("# demo/0001", r.stdout)
        self.assertIn("# demo/0002", r.stdout)
        self.assertNotEqual(run(["-list", "9999", "--workspace", str(FIXTURE)], ROOT).returncode, 0)

    def test_plain_list_still_lists(self):
        r = run(["-list", "--workspace", str(FIXTURE)], ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0010", r.stdout)


if __name__ == "__main__":
    unittest.main()
