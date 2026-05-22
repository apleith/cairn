from datetime import datetime, time, timedelta
from pathlib import Path

from .config import ROOT, load, load_busy_blocks

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def in_quiet_hours(now: datetime = None) -> bool:
    now = now or datetime.now()
    cfg = load()["quiet_hours"]
    start = _parse_time(cfg["start"])
    end = _parse_time(cfg["end"])
    t = now.time()
    if start < end:
        return start <= t < end
    return t >= start or t < end


def in_recurring_busy(now: datetime = None) -> tuple[bool, str]:
    now = now or datetime.now()
    horizon = now + timedelta(minutes=load()["calendar"]["check_horizon_minutes"])
    day_name = DAYS[now.weekday()]
    for block in load_busy_blocks():
        if block["day"] != day_name:
            continue
        b_start = datetime.combine(now.date(), _parse_time(block["start"]))
        b_end = datetime.combine(now.date(), _parse_time(block["end"]))
        if _overlaps(now, horizon, b_start, b_end):
            return True, block.get("label", f"{block['day']} {block['start']}-{block['end']}")
    return False, ""


def in_google_calendar_busy(now: datetime = None) -> tuple[bool, str]:
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
    except ImportError:
        return False, ""

    cfg = load()["calendar"]
    token_path = ROOT / cfg["oauth_token_path"]
    if not token_path.exists():
        return False, ""

    now = now or datetime.now()
    horizon = now + timedelta(minutes=cfg["check_horizon_minutes"])

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), ["https://www.googleapis.com/auth/calendar.readonly"])
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        events = service.events().list(
            calendarId="primary",
            timeMin=now.astimezone().isoformat(),
            timeMax=horizon.astimezone().isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        for event in events.get("items", []):
            if event.get("transparency") == "transparent":
                continue
            summary = event.get("summary", "Busy")
            return True, summary
    except Exception as e:
        print(f"[calendar_gate] Google Calendar check failed: {e}")
        return False, ""

    return False, ""


def should_suppress(now: datetime = None) -> tuple[bool, str]:
    """Return (suppress, reason). False means go ahead and notify."""
    now = now or datetime.now()
    if in_quiet_hours(now):
        return True, "quiet hours"
    busy, label = in_recurring_busy(now)
    if busy:
        return True, f"recurring block: {label}"

    provider = (load()["calendar"].get("provider") or "none").lower()
    horizon = load()["calendar"]["check_horizon_minutes"]
    if provider == "outlook":
        from .outlook_gate import in_outlook_busy
        busy, label = in_outlook_busy(now, horizon_minutes=horizon)
        if busy:
            return True, f"outlook: {label}"
    elif provider == "google":
        busy, label = in_google_calendar_busy(now)
        if busy:
            return True, f"calendar: {label}"
    return False, ""


def _parse_time(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end
