"""hee_date (bash) and hee_day.local_dates (Python) print time as the user's `date` does.

Operator, 2026-09-11: "format it exactly like the default date command on the
local system" and "if I change my settings to default to another iso type, our
tools (all) should report time in the same format as the current user". The two
helpers must agree with `date` and with each other under any TZ, locale and
HEE_DATE_FORMAT, read at call time."""
import os, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHFN = ROOT / "library" / "bash" / "vis.date.shfn.bash"
sys.path.insert(0, str(ROOT / "library" / "py"))

STAMPS = ["2026-09-11T19:47:37Z", "2026-09-11T14:47:37-05:00", "2026-09-11 19:47:37", "@1789156057",
          "2026-01-15T08:00:00+00:00", "2026-09-11", "not a stamp", ""]
SETTINGS = [{"TZ": "America/Chicago"}, {"TZ": "UTC", "LC_ALL": "C"}, {"TZ": "Europe/Berlin", "HEE_DATE_FORMAT": "%F %T %Z"},
            {"TZ": "Asia/Tokyo", "HEE_DATE_FORMAT": "+%Y-%m-%dT%H:%M:%S%z"}]


def env_for(extra):
    env = {k: v for k, v in os.environ.items() if k not in ("TZ", "LC_ALL", "LC_TIME", "HEE_DATE_FORMAT")}
    env.update(extra)
    return env


class DateParity(unittest.TestCase):
    def test_bash_python_and_date_agree(self):
        for extra in SETTINGS:
            env = env_for(extra)
            bash = subprocess.run(["bash", "-c", '. "$1"; shift; hee_date "$@"', "x", str(SHFN), *STAMPS],
                                  capture_output=True, text=True, env=env).stdout.split("\n")[:len(STAMPS)]
            py = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, sys.argv[1]); "
                                 "from hee_day import local_dates; print(json.dumps(local_dates(json.loads(sys.argv[2]))))",
                                 str(ROOT / "library" / "py"), __import__("json").dumps(STAMPS)],
                                capture_output=True, text=True, env=env)
            py = __import__("json").loads(py.stdout)
            self.assertEqual(bash, py, extra)
            fmt = extra.get("HEE_DATE_FORMAT")
            want = subprocess.run(["date", "-d", "@1789156057"] + (["+" + fmt.lstrip("+")] if fmt else []),
                                  capture_output=True, text=True, env=env).stdout.strip()
            self.assertEqual(py[0], want, extra)
            self.assertEqual(py[3], want, extra)
            self.assertEqual(py[5:], ["2026-09-11", "not a stamp", ""], extra)

    def test_settings_are_read_on_demand(self):
        from hee_day import local_date
        old = {k: os.environ.get(k) for k in ("TZ", "HEE_DATE_FORMAT")}
        try:
            os.environ["TZ"] = "UTC"; os.environ["HEE_DATE_FORMAT"] = "%H:%M"
            self.assertEqual(local_date("2026-09-11T19:47:37Z"), "19:47")
            os.environ["TZ"] = "America/Chicago"
            self.assertEqual(local_date("2026-09-11T19:47:37Z"), "14:47")
        finally:
            for k, v in old.items():
                if v is None: os.environ.pop(k, None)
                else: os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
