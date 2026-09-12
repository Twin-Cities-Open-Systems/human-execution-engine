#!/usr/bin/env python3
"""hee inv add: one inventory.asset record from a request document -- run
against temp git repos and a temp HOME, never the real dataset.

Run: python3 -m unittest tests/test_hee_inv_add.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tooling" / "bin" / "hee-inv"
sys.path.insert(0, str(ROOT / "library" / "py"))
import hee_inv  # noqa: E402

try:
    import yaml
except ImportError:  # the renderer needs no YAML library; only the round-trip test does
    yaml = None

OBS = "2026-09-12T06:20:50Z"


def planned(**over):
    doc = {
        "schema": "hee.inventory.asset-request.v1", "name": "firewall", "asset_type": "firewall",
        "sub": "electronics", "bucket": "durable", "lifecycle": "planned", "stableid": "athena",
        "vendor": "Qotom", "model": None, "serial": None, "observed": OBS,
        "requirements": ["Six ports", 'Intel NICs, "i226"'],
        "refs": ["https://github.com/Twin-Cities-Open-Systems/fleet-ops/issues/544"],
        "source": {"via": "cli"}, "notes": "no: not a boolean",
    }
    doc.update(over)
    return doc


class TestAdd(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ws = Path(self.tmp.name)
        self.home = ws / "home"
        (self.home / ".hee" / "index").mkdir(parents=True)
        (self.home / ".hee" / "index" / "_.yaml").write_text("hee-soa.v1: {}\n")
        self.repo = ws / "tcos-plan-private"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin",
                        "https://github.com/Twin-Cities-Open-Systems/tcos-plan-private.git"], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def run_add(self, doc, *extra, repo=None):
        f = Path(self.tmp.name) / "doc.json"
        f.write_text(doc if isinstance(doc, str) else json.dumps(doc))
        env = dict(os.environ, HOME=str(self.home), HEE_STATUS_STYLE="plain")
        return subprocess.run(["sh", str(TOOL), "add", "--json", str(f), "--tcos-repo", str(repo or self.repo), *extra],
                              capture_output=True, text=True, env=env)

    def test_planned_record_written_and_path_printed(self):
        r = self.run_add(planned())
        self.assertEqual(r.returncode, 0, r.stderr)
        rel = "inventory/objects/asset/20260912t062050z__inv-asset-electronics-athena.yaml"
        self.assertEqual(r.stdout.strip(), rel)
        self.assertIn("OK wrote " + rel, r.stderr)
        text = (self.repo / rel).read_text()
        self.assertIn("    inv.lifecycle: planned\n", text)
        self.assertIn("    serial: null\n", text)
        self.assertIn("    evidence: []\n", text)

    @unittest.skipUnless(yaml, "PyYAML not installed")
    def test_round_trips_through_a_yaml_reader(self):
        self.run_add(planned())
        f = next((self.repo / "inventory/objects/asset").glob("*.yaml"))
        d = yaml.safe_load(f.read_text())
        self.assertEqual(d["metadata"]["name"], "inv-asset-electronics-athena")
        self.assertEqual(d["spec"]["asset"]["requirements"][1], 'Intel NICs, "i226"')
        self.assertEqual(d["spec"]["asset"]["notes"], "no: not a boolean")
        self.assertIsNone(d["spec"]["asset"]["model"])
        self.assertEqual(d["metadata"]["labels"]["hee.object"], "true")

    def test_existing_name_is_critical(self):
        self.assertEqual(self.run_add(planned()).returncode, 0)
        r = self.run_add(planned(observed="2026-09-13T00:00:00Z"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("already exists", r.stderr)

    def test_contract_breaks_are_critical_with_the_field_named(self):
        for doc, word in [(planned(sub="gadgets"), "sub:"), (planned(lifecycle="wishlist"), "lifecycle:"),
                          (planned(color="red"), "unknown field"), (planned(stableid="Athena"), "stableid:"),
                          (planned(interfaces=[{"role": "wired", "mac": "nope"}]), "interfaces[0].mac"),
                          (planned(refs=["file:///etc/passwd"]), "refs[0]"), (planned(schema="v0"), "schema:"),
                          (planned(name=""), "name:"), ("{not json", "not valid UTF-8 JSON")]:
            r = self.run_add(doc)
            self.assertEqual(r.returncode, 2, (word, r.stderr))
            self.assertIn(word, r.stderr)
        self.assertFalse((self.repo / "inventory").exists())

    def test_stableid_falls_back_to_serial_then_type_and_time(self):
        r = self.run_add(planned(stableid=None, serial="NAA3XA1B", lifecycle="in_service"))
        self.assertTrue(r.stdout.strip().endswith("__inv-asset-electronics-naa3xa1b.yaml"), r.stdout)
        r = self.run_add(planned(stableid=None, serial=None, asset_type="camera"))
        self.assertTrue(r.stdout.strip().endswith("__inv-asset-electronics-camera-20260912t062050z.yaml"), r.stdout)

    def test_mac_normalized(self):
        r = self.run_add(planned(interfaces=[{"role": "wireless", "mac": "B8-27-EB-F2-D1-34"}]))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('        mac: "b8:27:eb:f2:d1:34"\n', (self.repo / r.stdout.strip()).read_text())

    def test_dry_run_prints_the_record_and_writes_nothing(self):
        r = self.run_add(planned(), "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("apiVersion: hee/v1\n"))
        self.assertFalse((self.repo / "inventory").exists())

    def test_unusable_targets_are_unknown(self):
        other = Path(self.tmp.name) / "other"
        subprocess.run(["git", "init", "-q", str(other)], check=True)
        r = self.run_add(planned(), repo=other)
        self.assertEqual(r.returncode, 3)
        self.assertIn("origin is not", r.stderr)
        (self.home / ".hee" / "index" / "_.yaml").unlink()
        self.assertEqual(self.run_add(planned()).returncode, 3)
        env = dict(os.environ, HOME=str(self.home))
        self.assertEqual(subprocess.run(["sh", str(TOOL), "add"], capture_output=True, env=env).returncode, 3)

    def test_allowed_values_come_from_the_contract(self):
        v = hee_inv.contract_values()
        self.assertIn("electronics", v["inv.sub"])
        self.assertEqual(v["inv.lifecycle"], ["planned", "ordered", "received", "in_service", "repurpose", "retired"])
        self.assertEqual(v["inv.bucket"], ["consumable", "durable", "commodity", "unknown"])


if __name__ == "__main__":
    unittest.main()
