#!/usr/bin/env python3
"""hee-name is deprecated (operator, 2026-10-01): -allocate refuses unless
HEE_NAME_ALLOW_DEPRECATED=1; the wind-down verbs keep working.

Every run uses a scratch --allocations-dir, so nothing touches a real ledger.
"""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tooling", "bin", "hee-name")


def run(args, extra_env=None):
    env = {k: v for k, v in os.environ.items() if k != "HEE_NAME_ALLOW_DEPRECATED"}
    env.update(extra_env or {})
    return subprocess.run([sys.executable, TOOL, *args], env=env,
                          capture_output=True, text=True, timeout=30)


class HeeNameDeprecated(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_help_leads_with_deprecation(self):
        r = run(["--help"])
        self.assertEqual(r.returncode, 0)
        # The man page tagline is the first paragraph after usage.
        after_usage = r.stdout.split("\n\n", 1)[1]
        self.assertTrue(after_usage.startswith("DEPRECATED"), after_usage[:80])
        self.assertIn("haproxy-1", r.stdout)

    def test_allocate_refuses_without_override(self):
        r = run(["-allocate", "--pool", "simpsons", "--scope", "pve-lxc",
                 "--allocations-dir", self.dir])
        self.assertEqual(r.returncode, 2)
        self.assertIn("CRITICAL", r.stderr)
        self.assertIn("deprecated", r.stderr)
        self.assertEqual(r.stdout, "")
        # Refused means nothing was written to the ledger.
        self.assertEqual(os.listdir(self.dir), [])

    def test_override_still_allocates_and_release_winds_down(self):
        env = {"HEE_NAME_ALLOW_DEPRECATED": "1"}
        r = run(["-allocate", "--pool", "simpsons", "--scope", "pve-lxc",
                 "--allocations-dir", self.dir], env)
        self.assertEqual(r.returncode, 0, r.stderr)
        name = r.stdout.strip()
        self.assertTrue(name)
        listed = run(["-list", "--scope", "pve-lxc", "--allocations-dir", self.dir])
        self.assertEqual(listed.returncode, 0)
        self.assertIn(name, listed.stdout)
        # -release needs no override: winding down must always work.
        rel = run(["-release", name, "--scope", "pve-lxc", "--allocations-dir", self.dir])
        self.assertEqual(rel.returncode, 0, rel.stderr)

    def test_list_pools_still_works(self):
        r = run(["-list-pools", "--allocations-dir", self.dir])
        self.assertEqual(r.returncode, 0)
        self.assertIn("simpsons", r.stdout)


if __name__ == "__main__":
    unittest.main()
