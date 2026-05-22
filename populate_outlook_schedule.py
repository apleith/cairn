"""DISABLED 2026-05-09 — populate-Outlook-with-routine-reminders policy retired.

Reason: the daily-routine series (lunch, morning pills, afternoon
drink, evening fluid, etc.) created hundreds of micro-events on the calendar
that drowned out actual meetings and work blocks. Those reminders now live
ONLY on:

  1. ntfy push (driven by the Cairn scheduler reading schedules.yaml);
  2. The PWA pull surface at http://<your-host>:5151/ (home-screen icon).

Outlook is reserved for things that actually consume time: meetings,
appointments, work blocks.

Re-enabling: if you ever want a SUBSET of routine reminders back on the
calendar (e.g., just morning weight check-in), don't reverse this guard.
Instead, write a new minimal script that pushes only those specific subjects.
The full populate-everything-from-schedules.yaml model is the policy that
got retired.

Original docstring preserved below for context.

----------
Populate Outlook with recurring daily appointments from schedules.yaml.

Creates one recurring-daily series per reminder, from 2026-04-18 through
2026-08-16 (configurable via CLI flags). Tagged with the marker
'life-os daily routine' so re-runs cleanly replace prior series.

Events are BusyStatus=Free (BusyStatus=0) so colleagues see nothing on
free/busy — these are personal routines, not scheduling blocks. Outlook
reminders are disabled so ntfy (the primary notification channel) isn't
doubled up.

Usage:
    python populate_outlook_schedule.py                      # default range
    python populate_outlook_schedule.py --start 2026-04-18 --end 2026-08-16
    python populate_outlook_schedule.py --clear              # wipe only
    python populate_outlook_schedule.py --dry-run            # preview
"""
import sys

print(
    "populate_outlook_schedule.py is DISABLED (2026-05-09). "
    "Read the docstring at the top of this file for the rationale and the "
    "alternative re-enablement path. No changes were made to your calendar."
)
sys.exit(0)


# --- Original implementation preserved below; never executes due to sys.exit() above. ---

import argparse
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.schedules import load as load_schedules
from src.config import ROOT

import win32com.client

OL_APPOINTMENT_ITEM = 1
OL_FREE = 0
OL_TENTATIVE = 1
OL_RECURS_DAILY = 0
OL_RECURS_WEEKLY = 1

# Outlook DayOfWeekMask bit values. Sum the bits of the allowed weekdays.
DAY_MASK = {
    "Sunday": 1,
    "Monday": 2,
    "Tuesday": 4,
    "Wednesday": 8,
    "Thursday": 16,
    "Friday": 32,
    "Saturday": 64,
}

ROUTINE_MARKER = "life-os daily routine"

DEFAULT_DURATION_MIN = 15
DURATION_OVERRIDES = {
    "meds_am_6": 5,
    "meds_am_8": 5,
    "meds_pm_8": 5,
    "weigh_in": 5,
    "hydrate_mid_morning": 5,
    "hydrate_afternoon": 5,
    "hydrate_evening": 5,
    "day_prep": 30,
    "breakfast": 15,
    "lunch": 30,
    "dinner": 45,
    "sleep_prep": 20,
}

CATEGORY = "Personal"


def _to_com_time(dt: datetime) -> datetime:
    """Compensate for pywin32 UTC-offset write bug (see reference_pywin32_outlook_tz.md)."""
    utc_offset = datetime.now().astimezone().utcoffset() or timedelta(0)
    return dt + utc_offset


def _outlook():
    return win32com.client.Dispatch("Outlook.Application")


def clear_existing(marker: str = ROUTINE_MARKER) -> list[str]:
    """Delete all appointment masters carrying the routine marker."""
    ns = _outlook().GetNamespace("MAPI")
    calendar = ns.GetDefaultFolder(9)
    items = calendar.Items
    items.IncludeRecurrences = False  # we want the masters, not expanded instances

    to_delete = []
    for item in items:
        try:
            cats = (item.Categories or "")
            if marker in cats:
                to_delete.append((item.Subject, item))
        except Exception:
            continue

    deleted = []
    for subject, item in to_delete:
        try:
            item.Delete()
            deleted.append(subject)
        except Exception as e:
            print(f"  failed to delete '{subject}': {e}")
    return deleted


def create_series(
    reminder: dict,
    start_date: date,
    end_date: date,
    marker: str = ROUTINE_MARKER,
) -> str:
    h, m = map(int, reminder["time"].split(":"))
    first_start = datetime.combine(start_date, dtime(h, m))
    duration = DURATION_OVERRIDES.get(reminder["id"], DEFAULT_DURATION_MIN)

    app = _outlook()
    appt = app.CreateItem(OL_APPOINTMENT_ITEM)
    appt.Subject = reminder["title"]
    appt.Body = reminder.get("message", "")
    appt.Start = _to_com_time(first_start)
    appt.Duration = duration
    appt.BusyStatus = OL_FREE
    appt.ReminderSet = False

    cats = [CATEGORY, marker]
    appt.Categories = ", ".join(cats)

    # Configure recurrence. If the reminder specifies a `days:` list, use a
    # weekly pattern restricted to those days. Otherwise default to daily.
    pattern = appt.GetRecurrencePattern()
    allowed_days = reminder.get("days") or []
    if allowed_days:
        mask = 0
        for d in allowed_days:
            mask |= DAY_MASK.get(d, 0)
        pattern.RecurrenceType = OL_RECURS_WEEKLY
        pattern.Interval = 1
        pattern.DayOfWeekMask = mask
    else:
        pattern.RecurrenceType = OL_RECURS_DAILY
        pattern.Interval = 1
    pattern.PatternStartDate = start_date.strftime("%m/%d/%Y")
    pattern.PatternEndDate = end_date.strftime("%m/%d/%Y")
    pattern.Duration = duration
    pattern.StartTime = _to_com_time(datetime.combine(date.today(), dtime(h, m)))

    appt.Save()
    return appt.Subject


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2026-04-18", help="First date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-08-16", help="Last date (YYYY-MM-DD)")
    parser.add_argument("--clear", action="store_true", help="Only clear existing; do not create")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    start_d = date.fromisoformat(args.start)
    end_d = date.fromisoformat(args.end)

    reminders = load_schedules()
    print(f"Loaded {len(reminders)} reminders from schedules.yaml")
    print(f"Range: {start_d} through {end_d}  ({(end_d - start_d).days + 1} days)")
    print(f"Marker: '{ROUTINE_MARKER}'  |  BusyStatus: Free  |  Outlook reminders: off")
    print()

    if args.dry_run:
        print("DRY-RUN — would clear + create:")
        for r in reminders:
            dur = DURATION_OVERRIDES.get(r["id"], DEFAULT_DURATION_MIN)
            print(f"  {r['time']}  ({dur:>2} min)  {r['id']:<22}  {r['title']}")
        return

    print("Clearing any prior series with routine marker...")
    deleted = clear_existing()
    print(f"  Deleted {len(deleted)} prior master(s): {deleted}")
    print()

    if args.clear:
        return

    print("Creating recurring series:")
    for r in reminders:
        subj = create_series(r, start_d, end_d)
        dur = DURATION_OVERRIDES.get(r["id"], DEFAULT_DURATION_MIN)
        print(f"  + {r['time']} [{dur:>2} min]  {subj}")

    print()
    print(f"Done. {len(reminders)} recurring series created in Outlook, daily {start_d} -> {end_d}.")


if __name__ == "__main__":
    main()
