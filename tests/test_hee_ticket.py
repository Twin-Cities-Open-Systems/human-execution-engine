#!/usr/bin/env python3
"""hee-ticket: the record fields the tool writes, the list filters, and the
-html render -- run against temp git repos, never this repo's tickets.

Run: python3 -m unittest tests/test_hee_ticket.py
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tooling" / "bin" / "hee-ticket"


def run(cwd, *args):
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=cwd, capture_output=True, text=True)


def mkrepo(d):
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    return d


class TestFieldsAndRender(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        self.a = mkrepo(self.ws / "alpha")
        self.b = mkrepo(self.ws / "beta")

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_records_source_ref_tags(self):
        r = run(self.a, "-new", "fix the thing", "--source", "todo.html T4", "--ref",
                "https://github.com/o/r/issues/7", "--tag", "view,docs")
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = (self.a / ".hee" / "tickets" / "0001.yaml").read_text()
        self.assertIn("source: todo.html T4", rec)
        self.assertIn("ref: https://github.com/o/r/issues/7", rec)
        self.assertIn("- view", rec)
        self.assertIn("- docs", rec)

    def test_close_records_why_and_list_filters(self):
        run(self.a, "-new", "one")
        run(self.a, "-new", "two")
        r = run(self.a, "-close", "1", "--why", "merged as #9")
        self.assertEqual(r.returncode, 0, r.stderr)
        import yaml
        rec = yaml.safe_load((self.a / ".hee/tickets/0001.yaml").read_text())
        self.assertEqual(rec["closed_reason"], "merged as #9")   # YAML quotes ' #', so match the value, not the text
        self.assertNotIn("0001", run(self.a, "-list", "--open").stdout)
        self.assertIn("0002", run(self.a, "-list", "--open").stdout)
        self.assertIn("0001", run(self.a, "-list", "--closed").stdout)
        self.assertNotIn("0002", run(self.a, "-list", "--closed").stdout)

    def test_html_strikes_closed_and_aggregates_workspace(self):
        run(self.a, "-new", "alpha open", "--ref", "https://github.com/o/alpha/issues/3")
        run(self.a, "-new", "alpha done")
        run(self.a, "-close", "2", "--why", "landed")
        run(self.b, "-new", "beta open <script>")
        r = run(self.a, "-html", "--workspace", str(self.ws))
        self.assertEqual(r.returncode, 0, r.stderr)
        h = r.stdout
        self.assertIn("<s>alpha done</s>", h)
        self.assertIn("landed", h)
        self.assertIn("alpha#3", h)
        self.assertIn("beta open &lt;script&gt;", h)            # escaped
        self.assertIn('data-tc-table', h)
        self.assertIn('data-tc-collapse="tickets-open"', h)
        self.assertIn("<b>2</b><span>open</span>", h)
        self.assertIn("<b>1</b><span>done</span>", h)

    def test_html_workspace_counts_each_origin_once(self):
        # alpha and a sibling clone of it share tickets; the workspace must list alpha once
        run(self.a, "-new", "shared ticket")
        subprocess.run(["git", "-C", str(self.a), "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.a), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "t"], check=True, capture_output=True)
        subprocess.run(["git", "clone", "-q", str(self.a), str(self.ws / "alpha-viewjs")], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.a), "remote", "add", "origin", "https://example.org/o/alpha.git"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.ws / "alpha-viewjs"), "remote", "set-url", "origin", "https://example.org/o/alpha"], check=True, capture_output=True)
        r = run(self.a, "-html", "--workspace", str(self.ws))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count("shared ticket"), 1)
        self.assertIn("from .hee/tickets in alpha", r.stdout)
        self.assertNotIn("alpha-viewjs", r.stdout)

    def test_html_single_repo_and_out_file(self):
        run(self.a, "-new", "only here")
        out = self.ws / "todo-body.html"
        r = run(self.a, "-html", "--out", str(out))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("only here", out.read_text())
        self.assertIn("from .hee/tickets in alpha", out.read_text())

    def test_html_workspace_without_tickets_refuses(self):
        empty = self.ws / "nothing"; empty.mkdir()
        r = run(self.a, "-html", "--workspace", str(empty))
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    sys.exit(unittest.main())
