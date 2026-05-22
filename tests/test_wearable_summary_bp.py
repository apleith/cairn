from datetime import date

from src.storage import connect, save_submission
from src.wearable_summary import summarize_bp, summarize_date


def _insert_bp(conn, uid, time_iso, sys, dia, pulse=None):
    conn.execute(
        "INSERT INTO hc_blood_pressure "
        "(hc_record_uid, time, systolic, diastolic, pulse_bpm, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, 'com.ihealthlabs.MyVitalsPro', 'Accu', '2026-05-12T09:00:00')",
        (uid, time_iso, sys, dia, pulse),
    )


def _insert_hr(conn, uid, time_iso, bpm):
    conn.execute(
        "INSERT INTO hc_heart_rate "
        "(hc_record_uid, time, bpm, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-12T09:00:00')",
        (uid, time_iso, bpm),
    )


def test_bp_returns_none_when_no_data(tmp_project):
    assert summarize_bp(date(2026, 5, 12)) is None


def test_bp_picks_latest_for_date(tmp_project):
    with connect() as conn:
        _insert_bp(conn, "uid-1", "2026-05-12T07:00:00", 132, 88, 70)
        _insert_bp(conn, "uid-2", "2026-05-12T08:15:00", 135, 94, 72)
    assert summarize_bp(date(2026, 5, 12)) == "135/94, 72 bpm"


def test_bp_correlates_pulse_from_heart_rate_when_null(tmp_project):
    with connect() as conn:
        _insert_bp(conn, "uid-1", "2026-05-12T08:15:00", 135, 94, None)
        _insert_hr(conn, "hr-1", "2026-05-12T08:14:30", 73)
        _insert_hr(conn, "hr-2", "2026-05-12T08:30:00", 80)  # outside +/-60s
    assert summarize_bp(date(2026, 5, 12)) == "135/94, 73 bpm"


def test_bp_no_pulse_when_no_hr_in_window(tmp_project):
    with connect() as conn:
        _insert_bp(conn, "uid-1", "2026-05-12T08:15:00", 135, 94, None)
        _insert_hr(conn, "hr-1", "2026-05-12T09:00:00", 80)
    assert summarize_bp(date(2026, 5, 12)) == "135/94"


def test_manual_bp_submission_blocks_overwrite(tmp_project):
    save_submission("bp", {"systolic": "120", "diastolic": "80", "pulse": "70"})
    with connect() as conn:
        _insert_bp(conn, "uid-1", "2026-05-12T08:15:00", 135, 94, 72)
    from datetime import datetime as _dt
    today = _dt.now().date()
    assert summarize_bp(today) is None


def test_summarize_date_writes_bp_to_health_log(tmp_project):
    with connect() as conn:
        _insert_bp(conn, "uid-1", "2026-05-12T08:15:00", 135, 94, 72)
    written = summarize_date(date(2026, 5, 12))
    assert "BP" in written
    log = (tmp_project / "health-log.md").read_text(encoding="utf-8")
    assert "**BP:** 135/94, 72 bpm #cardio" in log
