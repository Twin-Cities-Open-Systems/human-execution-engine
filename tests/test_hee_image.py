"""hee-image -- the firmware (serial) domain, without hardware.

What can be tested on a build host with no board and no ESP-IDF: the esptool
spelling shim across major versions, the profile.d env reader, the serial-device
gate, the build dry-run (the `# ci` example), and that flash on a path that is
neither a card nor a serial device stops at the block-device lookup and never
reaches esptool. The card domain is exercised by hand on flippy (mmcblk0) and
is deliberately not mocked here: a fake lsblk that passes says nothing.
"""

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tooling" / "bin" / "hee-image"


def load_tool():
    loader = importlib.machinery.SourceFileLoader("hee_image", str(TOOL))
    spec = importlib.util.spec_from_loader("hee_image", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def run(*args, env=None):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          check=False, env=env, cwd=ROOT)


class EsptoolSpelling(unittest.TestCase):
    def test_v5_keeps_hyphens_v4_gets_underscores(self):
        mod = load_tool()
        self.assertEqual(mod.et("write-flash", 5), "write-flash")
        self.assertEqual(mod.et("write-flash", 4), "write_flash")
        self.assertEqual(mod.et("--flash-mode", 4), "--flash_mode")
        self.assertEqual(mod.et("default-reset", 5), "default-reset")

    def test_classic_esp32_is_driven_at_the_safe_baud(self):
        mod = load_tool()
        self.assertEqual(mod.ESP32_SAFE_BAUD, "115200")
        self.assertNotEqual(mod.FLASH_BAUD, mod.ESP32_SAFE_BAUD)


class ProfileEnv(unittest.TestCase):
    def test_reads_idf_vars_from_profile_d_when_shell_did_not(self):
        mod = load_tool()
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as fh:
            fh.write('# comment\nexport IDF_PATH="/opt/esp/idf"\nexport IDF_TOOLS_PATH=/opt/esp\n')
            path = fh.name
        try:
            mod.IDF_PROFILE = path
            saved = {k: os.environ.pop(k) for k in ("IDF_PATH", "IDF_TOOLS_PATH") if k in os.environ}
            try:
                env = mod.idf_env()
            finally:
                os.environ.update(saved)
            self.assertEqual(env["IDF_PATH"], "/opt/esp/idf")
            self.assertEqual(env["IDF_TOOLS_PATH"], "/opt/esp")
        finally:
            os.unlink(path)

    def test_an_active_idf_shell_wins(self):
        mod = load_tool()
        os.environ["IDF_PATH"] = "/somewhere/else"
        try:
            self.assertEqual(mod.idf_env()["IDF_PATH"], "/somewhere/else")
        finally:
            del os.environ["IDF_PATH"]


class SerialGate(unittest.TestCase):
    def test_a_made_up_path_is_not_a_serial_device(self):
        mod = load_tool()
        self.assertFalse(mod.is_serial_device("/dev/ttyUSB999"))
        self.assertFalse(mod.is_serial_device("/dev/mmcblk0"))


class BuildDryRun(unittest.TestCase):
    def test_dry_run_exits_0_with_the_plan_and_builds_nothing(self):
        r = run("build", "--firmware", "espectre", "--chip", "esp32", "--dry-run",
                "--repo", "/nonexistent/espectre", "--out", "/nonexistent/out")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("dry run", r.stdout)
        self.assertIn("not present", r.stdout)
        self.assertFalse(Path("/nonexistent/out").exists())

    def test_missing_checkout_is_unknown_not_a_crash(self):
        r = run("build", "--firmware", "espectre", "--chip", "esp32", "--repo", "/nonexistent/espectre")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("no ESPectre checkout", r.stdout)


class FlashRouting(unittest.TestCase):
    def test_flash_on_a_path_that_is_no_device_stops_at_the_lookup(self):
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as fh:
            fh.write(b"\0" * 16)
            img = fh.name
        try:
            r = run("flash", "--image", img, "--device", "/dev/hee-image-no-such-device", "--yes")
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
            self.assertIn("no such block device", r.stdout)
        finally:
            os.unlink(img)

    def test_help_mentions_both_domains(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("flash (serial)", r.stdout)
        self.assertIn("hee image build", r.stdout)


if __name__ == "__main__":
    unittest.main()
