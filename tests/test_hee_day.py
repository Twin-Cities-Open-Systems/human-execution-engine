"""hee_day: a day is a calendar day in a named zone (glossary: Day).

Trigger, 2026-09-11: agents-live counted the UTC date, so jobs run at
19:48-23:49 CDT on 2026-09-10 showed as "spent today" on 2026-09-11.
"""
import datetime as dt
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "library" / "py"))
import hee_day  # noqa: E402

NOON_CDT = dt.datetime(2026, 9, 11, 17, 2, tzinfo=dt.timezone.utc)   # 12:02 CDT


class Day(unittest.TestCase):
    def test_default_is_utc_and_named(self):
        with mock.patch.dict(os.environ, {"HEE_DAY_TZ": ""}):
            w = hee_day.day_window(None, now=NOON_CDT)
        self.assertEqual((w["tz"], w["date"]), ("UTC", "2026-09-11"))
        self.assertIn("(UTC)", w["label"])

    def test_ledger_config_sets_the_zone_and_last_night_is_yesterday(self):
        with tempfile.TemporaryDirectory() as root, mock.patch.dict(os.environ, {"HEE_DAY_TZ": ""}):
            os.makedirs(os.path.join(root, ".hee"))
            open(os.path.join(root, ".hee", "config.yaml"), "w").write("dispatch:\n  day_tz: America/Chicago\n")
            w = hee_day.day_window(root, now=NOON_CDT)
        self.assertEqual((w["tz"], w["date"]), ("America/Chicago", "2026-09-11"))
        self.assertTrue(w["label"].startswith("2026-09-11 00:00-23:59 CDT"))
        self.assertFalse(hee_day.in_day("2026-09-11T04:49:00+00:00", w), "23:49 CDT on the 10th is yesterday")
        self.assertTrue(hee_day.in_day("2026-09-11T15:56:09+00:00", w), "10:56 CDT on the 11th is today")
        self.assertTrue(hee_day.in_day("2026-09-12T04:59:59+00:00", w), "23:59:59 CDT is still today")
        self.assertFalse(hee_day.in_day("2026-09-12T05:00:00+00:00", w), "midnight CDT is tomorrow")

    def test_env_overrides_config_and_bad_zone_raises(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".hee"))
            open(os.path.join(root, ".hee", "config.yaml"), "w").write("dispatch:\n  day_tz: America/Chicago\n")
            with mock.patch.dict(os.environ, {"HEE_DAY_TZ": "UTC"}):
                self.assertEqual(hee_day.day_window(root, now=NOON_CDT)["tz"], "UTC")
            with mock.patch.dict(os.environ, {"HEE_DAY_TZ": "Mars/Olympus"}):
                with self.assertRaises(ValueError):
                    hee_day.day_window(root)

    def test_dst_day_is_23_or_25_hours(self):
        with mock.patch.dict(os.environ, {"HEE_DAY_TZ": "America/Chicago"}):
            fall = hee_day.day_window(None, now=dt.datetime(2026, 11, 1, 15, 0, tzinfo=dt.timezone.utc))
        # same-zone subtraction is wall-clock (1 day); elapsed time is measured in UTC
        utc = dt.timezone.utc
        self.assertEqual(fall["end"].astimezone(utc) - fall["start"].astimezone(utc), dt.timedelta(hours=25))
        with mock.patch.dict(os.environ, {"HEE_DAY_TZ": "America/Chicago"}):
            spring = hee_day.day_window(None, now=dt.datetime(2027, 3, 14, 15, 0, tzinfo=dt.timezone.utc))
        self.assertEqual(spring["end"].astimezone(utc) - spring["start"].astimezone(utc), dt.timedelta(hours=23))


if __name__ == "__main__":
    unittest.main()
