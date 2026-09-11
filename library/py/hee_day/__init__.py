"""hee_day -- what "today" means for anything that sums, caps or reports by day.

A day is a calendar day, 00:00:00 to 23:59:59.999999, in a named IANA time
zone -- never "the last 24 hours", never an implied UTC. Records keep their
timestamps in UTC; the day is how they are grouped. Glossary: Day, Session.

Zone, first hit wins:
  1. $HEE_DAY_TZ                                  (per-oper override, heerc)
  2. <root>/.hee/config.yaml  dispatch.day_tz     (the ledger's own zone)
  3. UTC

Real trigger, 2026-09-11: agents-live read "spent today $4.00 / $10" at
noon in Minneapolis. The dispatcher and the page counted records started on
the current UTC date; UTC midnight is 19:00 CDT, so the previous evening's
jobs ($3.92) counted as today. Operator: "we did not spend $4 today ... what
is day? need to define in glossary, day vs session vs 00:00-23:59".
"""
import datetime as _dt
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TZ = "UTC"


def day_tz(root=None):
    """The IANA zone name that defines a day for ROOT's ledger."""
    env = os.environ.get("HEE_DAY_TZ", "").strip()
    if env:
        return env
    if root:
        cfg = os.path.join(os.fsdecode(root), ".hee", "config.yaml")
        if os.path.isfile(cfg):
            try:
                import yaml
                with open(cfg) as fh:
                    tz = ((yaml.safe_load(fh) or {}).get("dispatch") or {}).get("day_tz")
                if tz:
                    return str(tz).strip()
            except Exception:  # noqa: BLE001 -- an unreadable config falls through to the default, visibly named
                pass
    return DEFAULT_TZ


def day_window(root=None, now=None):
    """Today's window: {tz, date, start, end, label}. start/end are aware
    datetimes in the zone; end is exclusive (the next midnight). Raises
    ValueError for a zone name the system does not know."""
    name = day_tz(root)
    try:
        zone = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ValueError(f"unknown day time zone {name!r} (HEE_DAY_TZ or .hee/config.yaml dispatch.day_tz): {e}") from None
    now = (now or _dt.datetime.now(_dt.timezone.utc)).astimezone(zone)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = (start + _dt.timedelta(days=1, hours=2)).replace(hour=0, minute=0, second=0, microsecond=0)  # DST-safe next midnight
    label = f"{start.date().isoformat()} 00:00-23:59 {start.tzname()} ({name})"
    return {"tz": name, "date": start.date().isoformat(), "start": start, "end": end, "label": label}


def in_day(iso_ts, window):
    """True when the ISO-8601 timestamp ISO_TS falls inside WINDOW. A naive
    timestamp is read as UTC, which is how every hee record writes them."""
    if not iso_ts:
        return False
    try:
        t = _dt.datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
    except ValueError:
        return False
    if t.tzinfo is None:
        t = t.replace(tzinfo=_dt.timezone.utc)
    return window["start"] <= t < window["end"]
