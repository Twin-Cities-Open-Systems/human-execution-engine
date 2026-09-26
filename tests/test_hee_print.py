"""hee-print degrades honestly, and hee-tools-check enforces the pinned version.

The bug these lock down: on flippy the distro `yq` (a Python jq wrapper, 3.x)
was on PATH where hee-print expected the mikefarah yq (4.x). `yq -P` errored,
so every `hee print *.yaml` failed with exit 2 for days -- and hee-tools-check
reported `OK yq 3.4.3` because it checked presence, never the pinned version.

No network, no real yq/glow needed: a fake tool is placed first on PATH so the
degrade path is exercised deterministically on any host.
"""
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRINT = ROOT / "tooling" / "bin" / "hee-print"
TOOLS_CHECK = ROOT / "tooling" / "bin" / "hee-tools-check"
FIX = ROOT / "tests" / "fixtures" / "print"
MANI = ROOT / "tests" / "fixtures" / "tools-manifest"


def _run(argv, path_prefix=None, **kw):
    env = dict(os.environ)
    if path_prefix:
        env["PATH"] = f"{path_prefix}:{env['PATH']}"
    # plain style keeps the WARNING text stable regardless of the host's heerc
    env["HEE_STATUS_STYLE"] = "plain"
    return subprocess.run(
        argv, capture_output=True, text=True, env=env, cwd=str(ROOT), **kw
    )


def _fake_bin(dirpath, name, script):
    p = Path(dirpath) / name
    p.write_text("#!/bin/sh\n" + script)
    p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return p


class PrintRenders(unittest.TestCase):
    def test_json_renders_and_exits_zero(self):
        r = _run([str(PRINT), str(FIX / "sample.json")])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("hee-print", r.stdout)

    def test_yaml_renders_and_exits_zero(self):
        r = _run([str(PRINT), str(FIX / "sample.yaml")])
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_md_renders_and_exits_zero(self):
        r = _run([str(PRINT), str(FIX / "sample.md")])
        self.assertEqual(r.returncode, 0, r.stderr)


class PrintDegradesHonestly(unittest.TestCase):
    def test_wrong_yq_warns_but_still_renders_yaml(self):
        # A yq that errors on -P (exactly the Python yq's behavior) and whose
        # --version does not say "mikefarah". hee-print must NOT call `yq -P`,
        # must WARN on stderr, and must still exit 0 having rendered the file.
        with tempfile.TemporaryDirectory() as d:
            _fake_bin(
                d, "yq",
                'if [ "$1" = "--version" ]; then echo "yq 3.4.3"; exit 0; fi\n'
                'echo "yq: Unknown option -P" >&2; exit 2\n',
            )
            r = _run([str(PRINT), str(FIX / "sample.yaml")], path_prefix=d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("WARNING", r.stderr)
            self.assertNotIn("Unknown option -P", r.stderr)
            self.assertIn("tool", r.stdout)  # the yaml content came through

    def test_mikefarah_yq_is_used(self):
        with tempfile.TemporaryDirectory() as d:
            _fake_bin(
                d, "yq",
                'if [ "$1" = "--version" ]; then\n'
                '  echo "yq (https://github.com/mikefarah/yq/) version v4.50.1"; exit 0; fi\n'
                'echo MIKEFARAH-RAN; cat "$2" 2>/dev/null || cat "$1"\n',
            )
            r = _run([str(PRINT), str(FIX / "sample.yaml")], path_prefix=d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("MIKEFARAH-RAN", r.stdout)
            self.assertNotIn("WARNING", r.stderr)

    def test_missing_glow_warns_but_still_renders_md(self):
        # A curated PATH with the coreutils hee-print needs but NO glow, bat,
        # batcat, yq or jq -- so markdown degrades all the way to cat, with a
        # WARNING naming glow. Only tools that actually exist are linked in.
        import shutil
        need = ("sh", "dash", "bash", "realpath", "readlink", "dirname",
                "cat", "grep", "head", "sed", "tr", "cut", "awk", "file",
                "env", "printf", "wc", "tail")
        with tempfile.TemporaryDirectory() as d:
            for t in need:
                src = shutil.which(t)
                if src:
                    try:
                        os.symlink(src, Path(d) / t)
                    except OSError:
                        pass
            env = {"PATH": d, "HEE_STATUS_STYLE": "plain"}
            r = subprocess.run(
                [str(PRINT), str(FIX / "sample.md")],
                capture_output=True, text=True, env=env, cwd=str(ROOT),
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("glow", r.stderr)
            self.assertIn("WARNING", r.stderr)


class ToolsCheckEnforcesVersion(unittest.TestCase):
    def test_present_at_any_version_is_ok(self):
        r = _run([str(TOOLS_CHECK), str(MANI / "present.txt")])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_wrong_version_is_critical(self):
        r = _run([str(TOOLS_CHECK), str(MANI / "wrong-version.txt")])
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("wrong version", r.stdout)


if __name__ == "__main__":
    unittest.main()
