#!/usr/bin/env python3
"""hee inv: each subcommand checks only the commands it uses, and reports every
missing one at once as UNKNOWN (3) -- run with a PATH that lacks yq, exiftool
and unzip, never against the real dataset.

Run: python3 -m unittest tests/test_hee_inv_needs.py
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tooling" / "bin" / "hee-inv"
HIDDEN = {"yq", "exiftool", "unzip"}


class TestNeedsPerCommand(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        ws = Path(cls.tmp.name)
        cls.bin = ws / "bin"
        cls.bin.mkdir()
        for d in os.environ.get("PATH", "").split(os.pathsep):
            if not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                src = Path(d) / name
                dst = cls.bin / name
                if name in HIDDEN or dst.exists() or not (src.is_file() and os.access(src, os.X_OK)):
                    continue
                dst.symlink_to(src)
        cls.home = ws / "home"
        (cls.home / ".hee" / "index").mkdir(parents=True)
        (cls.home / ".hee" / "index" / "_.yaml").write_text("hee-soa.v1: {}\n")
        cls.repo = ws / "tcos-plan-private"
        subprocess.run(["git", "init", "-q", str(cls.repo)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_inv(self, *args):
        env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin))
        return subprocess.run(["/bin/sh", str(TOOL), *args], capture_output=True, text=True, env=env)

    def test_unknown_report_names_only_yq(self):
        r = self.run_inv("unknown", "report", "--tcos-repo", str(self.repo))
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("UNKNOWN missing command(s): yq", r.stdout)
        self.assertNotIn("exiftool", r.stdout)

    def test_ingest_names_every_missing_command_at_once(self):
        incoming = Path(self.tmp.name) / "incoming"
        incoming.mkdir(exist_ok=True)
        r = self.run_inv("ingest", str(incoming), "--tcos-repo", str(self.repo))
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("UNKNOWN missing command(s): exiftool unzip", r.stdout)
        self.assertNotIn("yq", r.stdout)

    def test_help_needs_nothing(self):
        r = self.run_inv("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("hee inv add", r.stdout)


if __name__ == "__main__":
    unittest.main()
