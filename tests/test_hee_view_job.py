"""hee view --job: a finished job's record is found by id or unique prefix and rendered."""
import importlib.machinery, importlib.util, os, subprocess, sys, tempfile, unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tooling" / "bin" / "hee-view"


class JobRecord(unittest.TestCase):
    def test_record_by_prefix_and_verdict_line(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"; (repo / ".hee" / "dispatch").mkdir(parents=True); (repo / ".git").mkdir()
            (repo / ".hee" / "dispatch" / "demo-20260911T000000Z.yaml").write_text(
                "job: demo-20260911T000000Z\nname: demo\nagent: ci-triage\nhostname: h\nvmid: 115\nticket: '0090'\nauth: wif\n"
                "federation_rule_id: fdrl_x\nstarted_at: a\nended_at: b\nbudget_usd: 4.0\ntimeout_s: 60\nexit: 0\ncost_usd: 1.5\n"
                "num_turns: 3\nmodels: [m]\nis_error: false\nresults_dir: results/demo\n")
            r = subprocess.run([sys.executable, str(TOOL), "--job", "demo-2026"], cwd=repo, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("auth wif", r.stdout); self.assertIn("cost $1.5", r.stdout); self.assertIn("rule fdrl_x", r.stdout)
            self.assertIn("finished, exit 0", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
