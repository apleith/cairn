from datetime import date

from src.storage import connect
from src.wearable_summary import summarize_date


def _seed_full_day(conn, anchor: date):
    iso_d = anchor.isoformat()
    # Sleep session ending 07:00 of anchor.
    conn.execute(
        "INSERT INTO hc_sleep_session "
        "(hc_record_uid, start_time, end_time, source_app, source_device, synced_at) "
        f"VALUES ('s1', '{anchor.year}-{anchor.month:02d}-{anchor.day-1:02d}T23:00:00', "
        f"'{iso_d}T07:00:00', 'com.samsung.health', 'Galaxy Fit 3', '{iso_d}T08:00:00')"
    )
    # RHR taken in the morning.
    conn.execute(
        "INSERT INTO hc_resting_heart_rate "
        "(hc_record_uid, time, bpm, source_app, source_device, synced_at) "
        f"VALUES ('r1', '{iso_d}T07:15:00', 60, 'com.samsung.health', 'Galaxy Fit 3', '{iso_d}T08:00:00')"
    )
    # Overnight SpO2 low.
    conn.execute(
        "INSERT INTO hc_oxygen_saturation "
        "(hc_record_uid, time, spo2_pct, source_app, source_device, synced_at) "
        f"VALUES ('o1', '{iso_d}T03:00:00', 93.0, 'com.samsung.health', 'Galaxy Fit 3', '{iso_d}T08:00:00')"
    )
    # Yesterday's steps (will land in today's 'prev day' field).
    if anchor.day > 1:
        prev = f"{anchor.year}-{anchor.month:02d}-{anchor.day-1:02d}"
        conn.execute(
            "INSERT INTO hc_steps "
            "(hc_record_uid, start_time, end_time, count, source_app, source_device, synced_at) "
            f"VALUES ('p1', '{prev}T10:00:00', '{prev}T11:00:00', 4500, 'com.samsung.health', 'Galaxy Fit 3', '{iso_d}T08:00:00')"
        )
    # Today's weight.
    conn.execute(
        "INSERT INTO hc_weight "
        "(hc_record_uid, time, weight_kg, source_app, source_device, synced_at) "
        f"VALUES ('w1', '{iso_d}T07:30:00', 279.1, 'com.renpho.app', 'Renpho Scale', '{iso_d}T08:00:00')"
    )


def test_summarize_date_writes_all_fields(tmp_project):
    anchor = date(2026, 5, 11)
    with connect() as conn:
        _seed_full_day(conn, anchor)

    written = summarize_date(anchor)

    text = (tmp_project / "health-log.md").read_text(encoding="utf-8")
    assert "## 2026-05-11, Monday" in text
    assert "**Sleep (wearable):** 8h 0m" in text
    assert "**Resting HR:** 60 bpm" in text
    assert "**SpO2 (overnight low):** 93%" in text
    assert "**Steps (prev day):** 4500" in text
    assert "**Weight:** 615.3" in text
    assert set(written) == {"Sleep (wearable)", "Resting HR", "SpO2 (overnight low)", "Steps (prev day)", "Weight"}


def test_summarize_date_skips_fields_with_no_data(tmp_project):
    anchor = date(2026, 5, 11)
    with connect() as conn:
        conn.execute(
            "INSERT INTO hc_weight "
            "(hc_record_uid, time, weight_kg, source_app, source_device, synced_at) "
            "VALUES ('w1', '2026-05-11T07:00:00', 279.1, 'com.renpho.app', 'Renpho Scale', '2026-05-11T08:00:00')"
        )

    written = summarize_date(anchor)
    assert written == ["Weight"]

    text = (tmp_project / "health-log.md").read_text(encoding="utf-8")
    assert "**Sleep (wearable):** —" in text
    assert "**Weight:** 615.3" in text
