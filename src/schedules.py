"""Fixed-time reminder loader + dispatch logic.

Reads schedules.yaml and fires any reminder whose configured time falls
within the last tick window and hasn't already fired today.
"""

from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from .config import ROOT

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def load() -> list[dict]:
    path = ROOT / "schedules.yaml"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("reminders") or []


def due_now(reminders: list[dict], now: datetime, window_minutes: int = 15) -> list[dict]:
    """Return reminders whose scheduled time is within [now - window, now]."""
    day_name = DAYS[now.weekday()]
    out = []
    for r in reminders:
        t = _parse_time(r["time"])
        sched = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        allowed_days = r.get("days") or DAYS
        if day_name not in allowed_days:
            continue
        delta = (now - sched).total_seconds() / 60.0
        if 0 <= delta < window_minutes:
            out.append(r)
    return out


def _parse_time(s: str):
    h, m = s.split(":")
    from datetime import time as dtime
    return dtime(int(h), int(m))
