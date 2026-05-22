from datetime import date

from src.storage import connect
from src.wearable_summary import summarize_resting_hr, summarize_spo2_overnight_low


def test_resting_hr_picks_latest_for_date(tmp_project):
    with connect() as conn:
        conn.execute(
            "INSERT INTO hc_resting_heart_rate "
            "(hc_record_uid, time, bpm, source_app, source_device, synced_at) "
            "VALUES ('uid-1', '2026-05-11T05:00:00', 58, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-11T08:00:00'), "
            "       ('uid-2', '2026-05-11T07:30:00', 62, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-11T08:00:00')"
        )
    assert summarize_resting_hr(date(2026, 5, 11)) == "62 bpm"


def test_resting_hr_returns_none_when_no_data(tmp_project):
    assert summarize_resting_hr(date(2026, 5, 11)) is None


def test_spo2_overnight_low(tmp_project):
    with connect() as conn:
        conn.execute(
            "INSERT INTO hc_oxygen_saturation "
            "(hc_record_uid, time, spo2_pct, source_app, source_device, synced_at) "
            "VALUES ('uid-1', '2026-05-10T23:30:00', 95.0, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-11T08:00:00'), "
            "       ('uid-2', '2026-05-11T02:15:00', 91.5, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-11T08:00:00'), "
            "       ('uid-3', '2026-05-11T06:00:00', 94.0, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-11T08:00:00')"
        )
    assert summarize_spo2_overnight_low(date(2026, 5, 11)) == "92%"


def test_spo2_returns_none_when_no_data(tmp_project):
    assert summarize_spo2_overnight_low(date(2026, 5, 11)) is None
