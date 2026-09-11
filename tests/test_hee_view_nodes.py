"""hee view --jobs: how each node performs next to the others, from the records alone."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VIEW = Path(__file__).resolve().parents[1] / "tooling" / "bin" / "hee-view"


def record(job, host, cost, wall, cpu=None, mem=None, out=1000, mistakes=0):
    r = {"job": job, "name": job.rsplit("-", 1)[0], "agent": host.split("-")[1], "hostname": host, "vmid": 100,
         "started_at": "2026-09-11T10:00:00+00:00", "cost_usd": cost, "exit": 0, "is_error": False,
         "duration_ms": wall * 1000, "usage": {"output_tokens": out}, "review": {"accepted": True, "mistakes": ["m"] * mistakes}}
    if cpu is not None:
        r["resources"] = {"wall_s": wall, "cpu_s": cpu, "mem_peak_mb": mem, "pids_peak": 20}
    return r


class Nodes(unittest.TestCase):
    def test_rollup_and_fleet_ratio(self):
        import yaml
        with tempfile.TemporaryDirectory() as root:
            d = Path(root) / ".hee" / "dispatch"; d.mkdir(parents=True); (Path(root) / ".git").mkdir()
            recs = [record("a-1", "tcos-media-x", 0.10, 60, cpu=20, mem=300, out=2000),
                    record("a-2", "tcos-media-x", 0.30, 120, cpu=40, mem=420, out=4000, mistakes=1),
                    record("b-1", "tcos-docs-y", 0.40, 90),
                    record("c-1", "tcos-review-z", 1.00, 200, cpu=80, mem=500, out=8000)]
            for r in recs:
                (d / f"{r['job']}.yaml").write_text(yaml.safe_dump(r))
            out = subprocess.run([sys.executable, str(VIEW), "--jobs", "--json", "--root", root], capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            nodes = json.loads(out.stdout)["nodes"]
            x = nodes["tcos-media-x"]
            self.assertEqual((x["jobs"], x["with_resources"], x["cost_per_job"], x["cpu_s_per_job"], x["mem_peak_mb"]), (2, 2, 0.2, 30.0, 420.0))
            self.assertEqual(x["out_tokens_per_cpu_s"], 100.0)
            self.assertEqual(x["mistakes_per_job"], 0.5)
            y = nodes["tcos-docs-y"]
            self.assertEqual((y["with_resources"], y["cpu_s_per_job"], y["wall_s_per_job"]), (0, None, 90.0))
            # fleet median cost/job over nodes: [0.2, 0.4, 1.0] -> 0.4
            self.assertEqual((x["cost_per_job_vs_fleet"], y["cost_per_job_vs_fleet"]), (0.5, 1.0))
            md = subprocess.run([sys.executable, str(VIEW), "--jobs", "--md", "--root", root], capture_output=True, text=True).stdout
            self.assertIn("| node | role | jobs | with resources |", md)


if __name__ == "__main__":
    unittest.main()
