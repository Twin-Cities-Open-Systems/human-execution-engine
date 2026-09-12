"""Nagios exit codes -- 0 OK, 1 WARNING, 2 CRITICAL, 3 UNKNOWN -- for the status
tools that did not follow them, measured 2026-09-11.

The operator, 2026-09-11: "make sure we are using 0123 ok,warn,fail,unknown -
should be nagios style everywhere". Every case here was a real exit code that
disagreed with the label the tool printed, or with the contract.
Run from the repo root: python3 -m unittest tests.test_nagios_exit_codes
"""
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "tooling" / "bin"
LIB = ROOT / "library" / "py"


def run(*cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=120, **kw)


class TestHeeStatusHelpers(unittest.TestCase):
    def test_argument_parser_usage_error_is_unknown(self):
        code = (f"import sys; sys.path.insert(0, {str(LIB)!r}); import hee_status; "
                "p = hee_status.ArgumentParser(prog='t'); p.add_argument('x'); p.parse_args([])")
        r = run(sys.executable, "-c", code)
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("UNKNOWN", r.stderr)

    def test_subparsers_inherit_the_unknown_exit(self):
        code = (f"import sys; sys.path.insert(0, {str(LIB)!r}); import hee_status; "
                "p = hee_status.ArgumentParser(prog='t'); s = p.add_subparsers(dest='cmd', required=True); "
                "a = s.add_parser('a'); a.add_argument('--n', type=int); p.parse_args(['a', '--n', 'x'])")
        self.assertEqual(run(sys.executable, "-c", code).returncode, 3)

    def test_exit_with_maps_status_int_none_and_message(self):
        cases = [("return hee_status.Status.WARNING", 1), ("return hee_status.Status.OK", 0),
                 ("return None", 0), ("return 2", 2), ("sys.exit(1)", 1),
                 ("sys.exit('cannot read the thing')", 3)]
        for body, want in cases:
            code = textwrap.dedent(f"""\
                import sys
                sys.path.insert(0, {str(LIB)!r})
                import hee_status
                def main():
                    {body}
                hee_status.exit_with(main)
                """)
            r = run(sys.executable, "-c", code)
            self.assertEqual(r.returncode, want, (body, r.stderr))


class TestUsageErrorsAreUnknown(unittest.TestCase):
    def test_argparse_status_tools(self):
        # Each exited 2 (argparse's default) before, before touching the network.
        for tool in ("hee-pve-health", "hee-view", "hee-board", "hee-quota"):
            r = run(sys.executable, BIN / tool, "--no-such-option")
            self.assertEqual(r.returncode, 3, f"{tool}: {r.stderr[-300:]}")
            self.assertIn("UNKNOWN", r.stderr, tool)

    def test_hee_check_unknown_subcommand(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(BIN / "hee-check", "no-such-subcommand", cwd=d)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)

    def test_hee_ver_unknown_subcommand(self):
        r = run(BIN / "hee-ver", "no-such-subcommand")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)

    def test_hee_filter_unknown_command(self):
        self.assertEqual(run(sys.executable, BIN / "hee-filter", "no-such-command").returncode, 3)


class TestHeeToolsCheck(unittest.TestCase):
    def check(self, manifest_text):
        with tempfile.TemporaryDirectory() as d:
            manifest = Path(d) / "tools.manifest.txt"
            manifest.write_text(manifest_text)
            return run(BIN / "hee-tools-check", manifest)

    def test_the_worst_line_is_the_exit_code(self):
        present = "git cmd any any required\n"
        self.assertEqual(self.check(present).returncode, 0)
        self.assertEqual(self.check(present + "hee-no-such-tool-zz cmd any any optional\n").returncode, 1)
        r = self.check("hee-no-such-tool-zz cmd any any optional\nhee-no-such-tool-yy cmd any any required\n")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_unreadable_manifest_is_unknown(self):
        r = run(BIN / "hee-tools-check", "/nonexistent/tools.manifest.txt")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("UNKNOWN", r.stdout + r.stderr)


class TestHeeLint(unittest.TestCase):
    def repo(self, d, body):
        subprocess.run(["git", "init", "-q", d], check=True, capture_output=True)
        (Path(d) / "obj.yaml").write_text(body)
        subprocess.run(["git", "-C", d, "add", "obj.yaml"], check=True)

    def test_error_mode_findings_are_critical(self):
        with tempfile.TemporaryDirectory() as d:
            self.repo(d, "apiVersion: hee/v1\nkind: Card\n")
            r = run(BIN / "hee-lint", "--mode", "error", cwd=d)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("CRITICAL", r.stdout)

    def test_outside_a_git_repo_is_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(BIN / "hee-lint", cwd=d)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)


class TestHeeFilterScan(unittest.TestCase):
    def test_scanner_unavailable_is_unknown(self):
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home)
            r = run(sys.executable, BIN / "hee-filter", "scan", input="hello\n", env=env)
        self.assertEqual(r.returncode, 3, r.stderr)

    @unittest.skipUnless((Path.home() / "git" / "tcos-audit" / "bin" / "scan_common.py").is_file(),
                         "tcos-audit is not checked out at ~/git/tcos-audit")
    def test_findings_are_critical(self):
        r = run(sys.executable, BIN / "hee-filter", "scan", input='key = "AKIAABCDEFGHIJKLMNOP"\n')
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("CRITICAL", r.stderr)


class TestHeeViewSites(unittest.TestCase):
    def test_unavailable_sitemap_is_unknown(self):
        r = run(sys.executable, BIN / "hee-view", "--sites", "--sites-only",
                "--sitemap", "/nonexistent/SITEMAP.yaml")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("UNKNOWN", r.stdout)


if __name__ == "__main__":
    unittest.main()
