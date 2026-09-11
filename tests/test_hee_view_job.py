"""hee view --job: a finished job's record is found by id or unique prefix and rendered."""
import importlib.machinery, importlib.util, os, subprocess, sys, tempfile, unittest
from unittest import mock
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tooling" / "bin" / "hee-view"


def _load():
    loader = importlib.machinery.SourceFileLoader("hee_view_under_test", str(TOOL))
    spec = importlib.util.spec_from_loader("hee_view_under_test", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


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


class JobsLive(unittest.TestCase):
    """jobs_live names the running job by claude's cwd and lists finished or
    stopped job dirs that have no record. Trigger, 2026-09-11: a job finished
    while its dispatcher was dead and never reached agents-live."""

    def test_running_and_unrecorded_split(self):
        m = _load()
        listing = ("118 review-x-20260911T042835Z finished\n"
                   "118 old-20260910T000000Z finished\n"
                   "116 media-y-20260911T050000Z running\n"
                   "115 dead-20260911T010000Z stopped\n"
                   "junk line\n")
        probes = []
        def fake_probe(host, jid, vmid=None):
            probes.append(jid)
            return {"vmid": int(vmid), "hostname": "h"}
        with mock.patch.object(m, "sh", return_value=(0, listing, "")), mock.patch.object(m, "job_live_probe", side_effect=fake_probe):
            running, unrecorded = m.jobs_live("pve", recorded={"old-20260910T000000Z"})
        self.assertEqual([(r["job"], r["state"]) for r in running], [("media-y-20260911T050000Z", "running")])
        self.assertEqual([(r["job"], r["state"]) for r in unrecorded],
                         [("review-x-20260911T042835Z", "finished"), ("dead-20260911T010000Z", "stopped")])
        self.assertNotIn("old-20260910T000000Z", probes)


if __name__ == "__main__":
    unittest.main()
