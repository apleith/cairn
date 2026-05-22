"""Cron entrypoint — called every 15 min by Task Scheduler.

Decides whether to fire prompts (weight, scales, activity) based on:
- quiet hours
- recurring busy blocks
- live Google Calendar
- per-prompt cadence and last-fired timestamps
"""

from datetime import date, datetime, timedelta

from . import activities, notify, schedules
from .calendar_gate import should_suppress, DAYS
from .config import load
from .storage import last_submission, save_submission, submissions_today


def run() -> None:
    cfg = load()
    now = datetime.now()
    public_url = cfg["app"]["public_url"]
    fired = []

    # Fixed-time reminders from schedules.yaml. Critical reminders bypass all
    # gates (quiet hours, busy-blocks, calendar). Non-critical ones respect them.
    for r in schedules.due_now(schedules.load(), now):
        rid = r["id"]
        if _reminder_fired_today(rid, now):
            continue
        critical = bool(r.get("critical"))
        if not critical:
            suppress, reason = should_suppress(now)
            if suppress:
                print(f"[scheduler] skipped reminder '{rid}' at {now.isoformat()}: {reason}")
                continue
        click = r.get("click_url")
        if click and not click.startswith(("http://", "https://")):
            click = f"{public_url}{click}"
        notify.send(
            title=r["title"],
            message=r.get("message", ""),
            click_url=click,
            tags=r.get("tags", ""),
            priority="high" if critical else None,
        )
        save_submission("reminder_fired", {"reminder_id": rid, "critical": critical}, subkind=rid)
        fired.append(f"reminder:{rid}")

    # Non-reminder prompts (scales + activity) still respect gates
    suppress, reason = should_suppress(now)
    if suppress:
        if fired:
            print(f"[scheduler] fired {fired}; further prompts suppressed: {reason}")
        else:
            print(f"[scheduler] suppressed at {now.isoformat()}: {reason}")
        return

    # Scales — cadence-driven
    for scale_cfg in cfg["scales"]["enabled"]:
        if _should_prompt_scale(scale_cfg, now):
            sid = scale_cfg["id"]
            notify.send(
                title=f"{sid.upper()} check-in",
                message=f"Tap to take the {sid.upper()}.",
                click_url=f"{public_url}/scale/{sid}",
                tags="brain",
            )
            fired.append(f"scale:{sid}")

    # Activity prompt — up to max_prompts_per_day, only when free
    if _should_prompt_activity(cfg, now):
        act = activities.pick_random()
        if act:
            notify.send(
                title=f"Activity nudge — {act['category']}",
                message=act["text"],
                click_url=f"{public_url}/activity/done?text={_urlencode(act['text'])}",
                tags="runner",
            )
            fired.append("activity")

    print(f"[scheduler] {now.isoformat()} fired: {fired or 'none'}")


def _reminder_fired_today(rid: str, now: datetime) -> bool:
    last = last_submission("reminder_fired", subkind=rid)
    if not last:
        return False
    last_date = datetime.fromisoformat(last["submitted_at"]).date()
    return last_date == now.date()


def _should_prompt_weight(cfg: dict, now: datetime) -> bool:
    # Retained for backward compat; schedules.yaml `weigh_in` is the primary path.
    target = _parse_hhmm(cfg["weight"]["prompt_time"])
    within = timedelta(minutes=15)
    target_dt = now.replace(hour=target[0], minute=target[1], second=0, microsecond=0)
    if abs((now - target_dt).total_seconds()) > within.total_seconds():
        return False
    last = last_submission("weight")
    if not last:
        return True
    last_date = datetime.fromisoformat(last["submitted_at"]).date()
    return last_date < now.date()


def _should_prompt_scale(scale_cfg: dict, now: datetime) -> bool:
    prompt_days = scale_cfg.get("prompt_on") or DAYS
    if DAYS[now.weekday()] not in prompt_days:
        return False

    # Only fire once per day, roughly morning
    if not (8 <= now.hour <= 11):
        return False

    sid = scale_cfg["id"]
    last = last_submission("scale", subkind=sid)
    if not last:
        return True

    last_dt = datetime.fromisoformat(last["submitted_at"])
    days_since = (now - last_dt).days
    return days_since >= scale_cfg.get("cadence_days", 7)


def _should_prompt_activity(cfg: dict, now: datetime) -> bool:
    if not (9 <= now.hour < 21):
        return False
    if submissions_today("activity_nudge") >= cfg["activities"]["max_prompts_per_day"]:
        return False
    # Randomize so we don't always fire at every 15-min tick
    import random
    return random.random() < 0.15


def _parse_hhmm(s: str) -> tuple[int, int]:
    h, m = s.split(":")
    return int(h), int(m)


def _urlencode(s: str) -> str:
    from urllib.parse import quote
    return quote(s)


if __name__ == "__main__":
    run()
