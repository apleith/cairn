import pytest

from src.storage import connect, insert_hc_record


def test_insert_steps_record(tmp_project):
    record = {
        "record_type": "Steps",
        "hc_record_uid": "uid-steps-1",
        "start_time": "2026-05-11T00:00:00",
        "end_time": "2026-05-11T01:00:00",
        "count": 305,
        "source_app": "com.samsung.health",
        "source_device": "Galaxy Fit 3",
    }
    inserted = insert_hc_record(record)
    assert inserted is True
    with connect() as conn:
        row = conn.execute("SELECT * FROM hc_steps WHERE hc_record_uid='uid-steps-1'").fetchone()
    assert row["count"] == 305
    assert row["source_app"] == "com.samsung.health"


def test_insert_is_idempotent(tmp_project):
    record = {
        "record_type": "RestingHeartRate",
        "hc_record_uid": "uid-rhr-1",
        "time": "2026-05-11T07:00:00",
        "bpm": 62,
        "source_app": "com.samsung.health",
        "source_device": "Galaxy Fit 3",
    }
    assert insert_hc_record(record) is True
    assert insert_hc_record(record) is False  # second call ignored
    with connect() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM hc_resting_heart_rate").fetchone()["c"]
    assert n == 1


def test_insert_unknown_record_type_raises(tmp_project):
    with pytest.raises(ValueError, match="unknown record type"):
        insert_hc_record({"record_type": "NotARealType", "hc_record_uid": "x"})


def test_insert_sleep_session_with_optional_fields(tmp_project):
    record = {
        "record_type": "SleepSession",
        "hc_record_uid": "uid-sleep-1",
        "start_time": "2026-05-10T23:00:00",
        "end_time": "2026-05-11T07:00:00",
        "title": None,
        "notes": None,
        "source_app": "com.samsung.health",
        "source_device": "Galaxy Fit 3",
    }
    assert insert_hc_record(record) is True
