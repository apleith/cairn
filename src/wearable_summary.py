"""Pure functions that derive daily health-log values from HC raw rows.

Each summarizer takes a date and returns either a formatted string (the
upsert value for health-log.md) or None if there is no data for that date.
The orchestrator (summarize_date) wires them up + upserts.
"""

from datetime import date, datetime, time, timedelta

from .storage import connect, upsert_health_log_field


def _wake_window(d: date) -> tuple[str, str]:
    """Return (start_iso, end_iso) that captures a sleep session that ENDS
    on date d. Sessions starting after 18:00 the prior day and ending before
    18:00 the given day are attributed to d as "the night ending in d's wake".
    """
    start = datetime.combine(d - timedelta(days=1), time(18, 0)).isoformat()
    end = datetime.combine(d, time(18, 0)).isoformat()
    return start, end


def summarize_sleep(d: date) -> str | None:
    start_iso, end_iso = _wake_window(d)
    with connect() as conn:
        session = conn.execute(
            "SELECT hc_record_uid, start_time, end_time FROM hc_sleep_session "
            "WHERE end_time >= ? AND end_time <= ? "
            "ORDER BY (julianday(end_time) - julianday(start_time)) DESC LIMIT 1",
            (start_iso, end_iso),
        ).fetchone()
        if not session:
            return None

        start_dt = datetime.fromisoformat(session["start_time"])
        end_dt = datetime.fromisoformat(session["end_time"])
        total_min = int(round((end_dt - start_dt).total_seconds() / 60))
        h, m = divmod(total_min, 60)
        total_str = f"{h}h {m}m"

        stages = conn.execute(
            "SELECT stage, start_time, end_time FROM hc_sleep_stage WHERE session_uid = ?",
            (session["hc_record_uid"],),
        ).fetchall()

    if not stages:
        return total_str

    by_stage: dict[str, float] = {"DEEP": 0.0, "REM": 0.0, "LIGHT": 0.0, "AWAKE": 0.0}
    for row in stages:
        s = datetime.fromisoformat(row["start_time"])
        e = datetime.fromisoformat(row["end_time"])
        minutes = (e - s).total_seconds() / 60
        key = row["stage"].upper()
        if key in by_stage:
            by_stage[key] += minutes

    total_staged = sum(by_stage.values())
    if total_staged <= 0:
        return total_str

    deep_pct = by_stage["DEEP"] / total_staged * 100
    rem_pct = by_stage["REM"] / total_staged * 100
    light_pct = by_stage["LIGHT"] / total_staged * 100
    awake_pct = by_stage["AWAKE"] / total_staged * 100

    raw = deep_pct * 2 + rem_pct * 1.5 + light_pct * 1 - awake_pct * 2
    score = max(0, min(100, int(round(raw))))
    return f"{total_str}, score {score}/100"


def summarize_resting_hr(d: date) -> str | None:
    """Return the latest RHR sample for the given date, formatted as 'N bpm'."""
    start_iso = datetime.combine(d, time.min).isoformat()
    end_iso = datetime.combine(d, time.max).isoformat()
    with connect() as conn:
        row = conn.execute(
            "SELECT bpm FROM hc_resting_heart_rate WHERE time >= ? AND time <= ? "
            "ORDER BY time DESC LIMIT 1",
            (start_iso, end_iso),
        ).fetchone()
    if not row:
        return None
    return f"{int(round(row['bpm']))} bpm"


def summarize_spo2_overnight_low(d: date) -> str | None:
    """Return the lowest SpO2 percentage during d's sleep window, rounded
    to integer %, formatted as 'N%'.
    """
    start_iso, end_iso = _wake_window(d)
    with connect() as conn:
        row = conn.execute(
            "SELECT MIN(spo2_pct) AS low FROM hc_oxygen_saturation "
            "WHERE time >= ? AND time <= ?",
            (start_iso, end_iso),
        ).fetchone()
    if not row or row["low"] is None:
        return None
    return f"{int(round(row['low']))}%"


_KG_TO_LB = 2.20462


def summarize_steps_for_walk_date(walk_date: date) -> str | None:
    """Sum every hc_steps interval whose start_time falls in walk_date.
    Caller decides whether to upsert this into walk_date's entry or
    walk_date + 1 day's 'Steps (prev day)' field.
    """
    start_iso = datetime.combine(walk_date, time.min).isoformat()
    end_iso = datetime.combine(walk_date, time.max).isoformat()
    with connect() as conn:
        row = conn.execute(
            "SELECT SUM(count) AS total FROM hc_steps "
            "WHERE start_time >= ? AND start_time <= ?",
            (start_iso, end_iso),
        ).fetchone()
    if not row or row["total"] is None:
        return None
    return str(int(row["total"]))


def _manual_bp_submitted_on(d: date) -> bool:
    """True if a manual /bp submission exists for date d. The PWA /bp route
    is the owner's deliberate cuff entry — when present, do not overwrite
    from auto-synced HC data.
    """
    day = d.isoformat()
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM submissions WHERE kind='bp' "
            "AND substr(submitted_at, 1, 10) = ? LIMIT 1",
            (day,),
        ).fetchone()
    return row is not None


def summarize_bp(d: date) -> str | None:
    """Latest BloodPressureRecord for d, formatted as 'sys/dia[, pulse bpm]'.

    HC's BloodPressureRecord doesn't carry pulse natively. If pulse_bpm is
    NULL, correlate with hc_heart_rate within +/-60s of the BP timestamp
    (mirrors the Android v0.3 reader).

    Returns None if no BP row for the date, or if a manual /bp submission
    already exists for d (precedence: manual cuff entry wins).
    """
    if _manual_bp_submitted_on(d):
        return None

    start_iso = datetime.combine(d, time.min).isoformat()
    end_iso = datetime.combine(d, time.max).isoformat()
    with connect() as conn:
        bp = conn.execute(
            "SELECT time, systolic, diastolic, pulse_bpm FROM hc_blood_pressure "
            "WHERE time >= ? AND time <= ? ORDER BY time DESC LIMIT 1",
            (start_iso, end_iso),
        ).fetchone()
        if not bp:
            return None

        sys_i = int(bp["systolic"])
        dia_i = int(bp["diastolic"])
        pulse = bp["pulse_bpm"]

        if pulse is None:
            bp_dt = datetime.fromisoformat(bp["time"])
            window_start = (bp_dt - timedelta(seconds=60)).isoformat()
            window_end = (bp_dt + timedelta(seconds=60)).isoformat()
            hr = conn.execute(
                "SELECT bpm FROM hc_heart_rate WHERE time >= ? AND time <= ? "
                "ORDER BY ABS(julianday(time) - julianday(?)) ASC LIMIT 1",
                (window_start, window_end, bp["time"]),
            ).fetchone()
            if hr:
                pulse = int(hr["bpm"])

    out = f"{sys_i}/{dia_i}"
    if pulse is not None:
        out += f", {int(pulse)} bpm"
    return out


def summarize_weight(d: date) -> str | None:
    """Latest weight record on d, converted kg -> lb, rounded to 1 decimal."""
    start_iso = datetime.combine(d, time.min).isoformat()
    end_iso = datetime.combine(d, time.max).isoformat()
    with connect() as conn:
        row = conn.execute(
            "SELECT weight_kg FROM hc_weight WHERE time >= ? AND time <= ? "
            "ORDER BY time DESC LIMIT 1",
            (start_iso, end_iso),
        ).fetchone()
    if not row:
        return None
    lb = round(row["weight_kg"] * _KG_TO_LB, 1)
    return f"{lb}"


def summarize_date(d: date) -> list[str]:
    """Compute all summarizable fields for date d, upsert each into
    health-log.md via target_date=d. Returns the list of field labels
    that had data and were written.
    """
    written: list[str] = []

    sleep = summarize_sleep(d)
    if sleep is not None:
        upsert_health_log_field("Sleep (wearable)", f"{sleep} #psych #pulm", target_date=d)
        written.append("Sleep (wearable)")

    rhr = summarize_resting_hr(d)
    if rhr is not None:
        upsert_health_log_field("Resting HR", f"{rhr} #cardio", target_date=d)
        written.append("Resting HR")

    spo2 = summarize_spo2_overnight_low(d)
    if spo2 is not None:
        upsert_health_log_field("SpO2 (overnight low)", f"{spo2} #pulm", target_date=d)
        written.append("SpO2 (overnight low)")

    steps_walked_yday = summarize_steps_for_walk_date(d - timedelta(days=1))
    if steps_walked_yday is not None:
        upsert_health_log_field(
            "Steps (prev day)", f"{steps_walked_yday} #bariatric #cardio", target_date=d
        )
        written.append("Steps (prev day)")

    weight = summarize_weight(d)
    if weight is not None:
        upsert_health_log_field("Weight", f"{weight} #bariatric #cardio #pulm", target_date=d)
        written.append("Weight")

    bp = summarize_bp(d)
    if bp is not None:
        upsert_health_log_field("BP", f"{bp} #cardio", target_date=d)
        written.append("BP")

    return written
