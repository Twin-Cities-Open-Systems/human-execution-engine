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


def _epoch(ts):
    """Seconds since the epoch for an ISO-8601 stamp, or None if it is not one."""
    import datetime as _dt
    import re
    t = str(ts if ts is not None else "").strip()
    if re.fullmatch(r"@\d+", t):
        return int(t[1:])
    # A date with no time of day is not a moment; it prints unchanged, as in
    # vis.date.shfn.bash.
    if not re.match(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", t):
        return None
    try:
        d = _dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=_dt.timezone.utc)
    return int(d.timestamp())


def local_dates(stamps):
    """Each ISO-8601 stamp as this machine's default `date` prints it.

    Operator, 2026-09-11: "format it exactly like the default date command on
    the local system". So `date` does the formatting: one `date -f -` call
    reads every stamp as @epoch, and the result carries the caller's TZ,
    LC_TIME, LC_ALL and LANG exactly as `date` would. Only for display in a
    terminal. Cursors, JSON and committed files stay ISO-8601 UTC, because a
    locale-shaped stamp would make the same file differ from machine to machine.

    On demand: nothing is cached, so a change to the operator's TZ or LC_TIME
    shows on the next call. $HEE_DATE_FORMAT, set in heerc, overrides the
    shape for every hee tool at once, as a `date` format such as %F %T %Z.
    Operator, 2026-09-11: "if I change my settings to default to another iso
    type, our tools (all) should report time in the same format as the
    current user".

    A stamp that does not parse comes back unchanged. When `date -f` is not
    available, busybox for one, Python prints the same shape in the C locale.
    """
    import datetime as _dt
    import subprocess
    stamps = list(stamps)
    epochs = [_epoch(s) for s in stamps]
    todo = [e for e in epochs if e is not None]
    shown = {}
    if todo:
        try:
            fmt = os.environ.get("HEE_DATE_FORMAT", "").strip()
            cmd = ["date", "-f", "-"] + (["+" + fmt.lstrip("+")] if fmt else [])
            r = subprocess.run(cmd, input="".join(f"@{e}\n" for e in todo),
                               capture_output=True, text=True, timeout=5)
            lines = r.stdout.splitlines()
            if r.returncode == 0 and len(lines) == len(todo):
                shown = dict(zip(todo, lines))
        except (OSError, subprocess.SubprocessError):
            pass
    out = []
    for s, e in zip(stamps, epochs):
        if e is None:
            out.append(s)
        elif e in shown:
            out.append(shown[e])
        else:
            out.append(_dt.datetime.fromtimestamp(e).astimezone().strftime("%a %b %e %I:%M:%S %p %Z %Y"))
    return out


def local_date(ts):
    """One stamp as this machine's default `date` prints it. See local_dates."""
    return local_dates([ts])[0]

