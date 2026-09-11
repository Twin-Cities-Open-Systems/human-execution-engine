"""hee view shows time the way the user's `date` does, and keeps UTC where it is stored.

Operator, 2026-09-11: "let's use system locale here" on the brain dump status,
then "format it exactly like the default date command on the local system", and
"our tools (all) should report time in the same format as the current user"."""
import os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "tooling" / "bin" / "hee-view"
MD = ("<!-- tc-braindump-entry 2026-09-11T19:40:45Z -->\n### 2026-09-11T19:40:45Z\n\nfirst\n\n"
      "<!-- tc-braindump-entry 2026-09-11T19:47:37Z -->\n### 2026-09-11T19:47:37Z\n\nsecond\n")


def date_of(epoch, env):
    return subprocess.run(["date", "-d", f"@{epoch}"], capture_output=True, text=True, env=env).stdout.strip()


class LocalTime(unittest.TestCase):
    def test_braindump_status_uses_the_users_date(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "dump.md"; f.write_text(MD)
            env = dict(os.environ, TZ="America/Chicago", XDG_STATE_HOME=d, HEE_VIEW_BRAINDUMP_URL=f.as_uri())
            env.pop("HEE_DATE_FORMAT", None)
            r = subprocess.run([sys.executable, str(VIEW), "--braindump"], capture_output=True, text=True, env=env)
            out = r.stdout + r.stderr
            self.assertIn("newest " + date_of(1789156057, env), out)
            self.assertNotIn("19:47:37Z", out)
            subprocess.run([sys.executable, str(VIEW), "--braindump", "--mark-seen"], capture_output=True, text=True, env=env)
            self.assertEqual((Path(d) / "hee" / "view-braindump.cursor").read_text().strip(), "2026-09-11T19:47:37Z", "the cursor stays UTC")

    def test_jobs_text_follows_heerc_format_and_md_stays_utc(self):
        env = dict(os.environ, TZ="UTC", HEE_DATE_FORMAT="%F %H:%M %Z")
        text = subprocess.run([sys.executable, str(VIEW), "--jobs", "--root", "tests/fixtures/dispatch"], cwd=ROOT, capture_output=True, text=True, env=env).stdout
        self.assertIn("2026-09-11 00:00 UTC", text)
        md = subprocess.run([sys.executable, str(VIEW), "--jobs", "--md", "--root", "tests/fixtures/dispatch"], cwd=ROOT, capture_output=True, text=True, env=env).stdout
        self.assertIn("| 2026-09-11T00:00 |", md)
        self.assertNotIn("UTC |", md)


if __name__ == "__main__":
    unittest.main()
