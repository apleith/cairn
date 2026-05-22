"""Outlook calendar reader — uses win32com to check local Outlook calendar.

Works with SIUE M365 / any Exchange account configured in the local Outlook client.
No OAuth, no cloud API. Reads the default calendar folder.
"""

from datetime import datetime, timedelta

# Outlook BusyStatus constants (olBusyStatus enum)
OL_FREE = 0
OL_TENTATIVE = 1
OL_BUSY = 2
OL_OUT_OF_OFFICE = 3
OL_WORKING_ELSEWHERE = 4

BLOCKING_STATUSES = {OL_BUSY, OL_OUT_OF_OFFICE, OL_TENTATIVE}


def in_outlook_busy(now: datetime = None, horizon_minutes: int = 15) -> tuple[bool, str]:
    """Return (True, label) if a blocking event overlaps now..now+horizon.

    Skips olFree events. Skips all-day events (they mark the whole day busy and
    would always fire).
    """
    try:
        import win32com.client
    except ImportError:
        return False, ""

    now = now or datetime.now()
    horizon = now + timedelta(minutes=horizon_minutes)

    try:
        app = win32com.client.Dispatch("Outlook.Application")
        ns = app.GetNamespace("MAPI")
        calendar = ns.GetDefaultFolder(9)
        items = calendar.Items
        items.IncludeRecurrences = True
        items.Sort("[Start]")

        filter_str = (
            f"[Start] <= '{_fmt(horizon)}' AND [End] >= '{_fmt(now)}'"
        )
        restricted = items.Restrict(filter_str)

        for item in restricted:
            try:
                if item.AllDayEvent:
                    continue
                if int(item.BusyStatus) not in BLOCKING_STATUSES:
                    continue
                label = (item.Subject or "Busy").strip() or "Busy"
                return True, label
            except Exception:
                continue

    except Exception as e:
        print(f"[outlook_gate] check failed: {e}")
        return False, ""

    return False, ""


def _fmt(dt: datetime) -> str:
    return dt.strftime("%m/%d/%Y %I:%M %p")
