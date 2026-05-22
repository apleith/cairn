from datetime import date

from src.storage import connect
from src.wearable_summary import summarize_steps_for_walk_date, summarize_weight


def test_steps_sums_all_intervals_in_day(tmp_project):
    with connect() as conn:
        conn.execute(
            "INSERT INTO hc_steps "
            "(hc_record_uid, start_time, end_time, count, source_app, source_device, synced_at) "
            "VALUES "
            "('u1', '2026-05-10T08:00:00', '2026-05-10T09:00:00', 1200, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-11T08:00:00'),"
            "('u2', '2026-05-10T12:00:00', '2026-05-10T13:00:00', 800, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-11T08:00:00'),"
            "('u3', '2026-05-10T18:00:00', '2026-05-10T19:00:00', 305, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-11T08:00:00')"
        )
    assert summarize_steps_for_walk_date(date(2026, 5, 10)) == "2305"


def test_steps_returns_none_when_no_data(tmp_project):
    assert summarize_steps_for_walk_date(date(2026, 5, 10)) is None


def test_weight_returns_latest_record_in_lb(tmp_project):
    with connect() as conn:
        conn.execute(
            "INSERT INTO hc_weight "
            "(hc_record_uid, time, weight_kg, source_app, source_device, synced_at) "
            "VALUES "
            "('w1', '2026-05-11T07:15:00', 279.1, 'com.renpho.app', 'Renpho Scale', '2026-05-11T08:00:00')"
        )
    assert summarize_weight(date(2026, 5, 11)) == "615.3"


def test_weight_returns_none_when_no_record(tmp_project):
    assert summarize_weight(date(2026, 5, 11)) is None


def test_weight_picks_latest_when_multiple(tmp_project):
    with connect() as conn:
        conn.execute(
            "INSERT INTO hc_weight "
            "(hc_record_uid, time, weight_kg, source_app, source_device, synced_at) "
            "VALUES "
            "('w1', '2026-05-11T07:00:00', 279.5, 'com.renpho.app', 'Renpho Scale', '2026-05-11T08:00:00'),"
            "('w2', '2026-05-11T07:30:00', 279.1, 'com.renpho.app', 'Renpho Scale', '2026-05-11T08:00:00')"
        )
    assert summarize_weight(date(2026, 5, 11)) == "615.3"
