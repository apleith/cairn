from datetime import date

from src.storage import connect
from src.wearable_summary import summarize_sleep


def _insert_session(conn, uid, start, end):
    conn.execute(
        "INSERT INTO hc_sleep_session "
        "(hc_record_uid, start_time, end_time, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-11T08:00:00')",
        (uid, start, end),
    )


def _insert_stage(conn, uid, session_uid, start, end, stage):
    conn.execute(
        "INSERT INTO hc_sleep_stage "
        "(hc_record_uid, session_uid, start_time, end_time, stage, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-11T08:00:00')",
        (uid, session_uid, start, end, stage),
    )


def test_summarize_sleep_returns_none_when_no_session(tmp_project):
    assert summarize_sleep(date(2026, 5, 11)) is None


def test_summarize_sleep_total_only_when_no_stages(tmp_project):
    with connect() as conn:
        _insert_session(conn, "sess-1", "2026-05-10T23:00:00", "2026-05-11T07:00:00")
    assert summarize_sleep(date(2026, 5, 11)) == "8h 0m"


def test_summarize_sleep_with_stages_includes_score(tmp_project):
    with connect() as conn:
        _insert_session(conn, "sess-1", "2026-05-10T23:00:00", "2026-05-11T07:00:00")
        _insert_stage(conn, "stg-1", "sess-1", "2026-05-10T23:00:00", "2026-05-11T00:00:00", "DEEP")
        _insert_stage(conn, "stg-2", "sess-1", "2026-05-11T00:00:00", "2026-05-11T01:30:00", "REM")
        _insert_stage(conn, "stg-3", "sess-1", "2026-05-11T01:30:00", "2026-05-11T06:30:00", "LIGHT")
        _insert_stage(conn, "stg-4", "sess-1", "2026-05-11T06:30:00", "2026-05-11T07:00:00", "AWAKE")
    result = summarize_sleep(date(2026, 5, 11))
    assert result == "8h 0m, score 100/100"


def test_summarize_sleep_attributes_overnight_to_wake_date(tmp_project):
    with connect() as conn:
        _insert_session(conn, "sess-1", "2026-05-10T22:30:00", "2026-05-11T05:45:00")
    assert summarize_sleep(date(2026, 5, 11)) == "7h 15m"
    assert summarize_sleep(date(2026, 5, 10)) is None
