"""Tests for the v1 fact-table storage helpers.

Each test relies on the shared tmp_project fixture so writes land in a
throwaway database, never touching the owner's real data.db.
"""
from src import storage


def test_save_daily_observation_full_row(tmp_project):
    obs_id = storage.save_daily_observation({
        "date": "2026-05-22",
        "weight_lb": 620.4,
        "weight_observed": True,
        "weight_source": "manual",
        "systolic": 128,
        "diastolic": 82,
        "pulse_from_bp_device": 68,
        "resting_hr": 62,
        "steps": 4823,
        "steps_observed": True,
        "sleep_hours": 6.5,
        "notes": "test",
        "source": "manual_form",
        "source_record_id": "sub:42",
    })
    assert obs_id is not None
    with storage.connect() as conn:
        row = conn.execute(
            "SELECT * FROM daily_observations WHERE id=?", (obs_id,)
        ).fetchone()
    assert row["date"] == "2026-05-22"
    assert row["weight_lb"] == 620.4
    assert row["weight_observed"] == 1  # SQLite stores bool as 1/0
    assert row["systolic"] == 128
    assert row["resting_hr"] == 62
    assert row["sleep_hours"] == 6.5
    assert row["source"] == "manual_form"
    assert row["source_record_id"] == "sub:42"
    # Unspecified columns stay NULL
    assert row["bp_posture"] is None
    assert row["max_hr"] is None
    # import_timestamp default fires
    assert row["import_timestamp"] is not None


def test_save_daily_observation_drops_none_values(tmp_project):
    storage.save_daily_observation({
        "date": "2026-05-22",
        "weight_lb": 620.0,
        "systolic": None,           # explicit None must be dropped
        "source": "manual_form",
    })
    with storage.connect() as conn:
        row = conn.execute("SELECT systolic FROM daily_observations").fetchone()
    assert row["systolic"] is None


def test_save_body_measurement(tmp_project):
    bm_id = storage.save_body_measurement({
        "date": "2026-05-22",
        "waist_in": 64.5,
        "hips_in": 70.0,
        "neck_in": 19.5,
        "measurement_time": "morning",
        "measurement_method": "self_measure",
        "notes": "tape only",
        "source": "manual_form",
    })
    assert bm_id is not None
    with storage.connect() as conn:
        row = conn.execute(
            "SELECT * FROM body_measurements WHERE id=?", (bm_id,)
        ).fetchone()
    assert row["waist_in"] == 64.5
    assert row["hips_in"] == 70.0
    assert row["upper_arm_in"] is None
    assert row["import_timestamp"] is not None


def test_save_medication_event_full_payload(tmp_project):
    ev_id = storage.save_medication_event({
        "date": "2026-05-22",
        "medication_name": "Mounjaro",
        "generic_name": "tirzepatide",
        "dose": "10 mg",
        "dose_numeric": 10.0,
        "dose_unit": "mg",
        "route": "injection",
        "frequency": "weekly",
        "event_type": "dose_change",
        "reason": "titration",
        "prescribing_context": "weight_management",
        "source": "manual_form",
    })
    with storage.connect() as conn:
        row = conn.execute(
            "SELECT * FROM medication_events WHERE id=?", (ev_id,)
        ).fetchone()
    assert row["medication_name"] == "Mounjaro"
    assert row["generic_name"] == "tirzepatide"
    assert row["dose_numeric"] == 10.0
    assert row["event_type"] == "dose_change"
    assert row["reason"] == "titration"


def test_save_clinical_event_with_sleep_study_fields(tmp_project):
    ev_id = storage.save_clinical_event({
        "date": "2026-06-15",
        "label": "In-lab PSG",
        "event_type": "sleep_study",
        "category": "sleep",
        "certainty": "confirmed",
        "ahi": 27.3,
        "cpap_pressure": "9 cmH2O",
        "cpap_hours": 6.5,
        "mask_type": "nasal pillow",
        "source": "manual_form",
    })
    with storage.connect() as conn:
        row = conn.execute(
            "SELECT * FROM clinical_events WHERE id=?", (ev_id,)
        ).fetchone()
    assert row["event_type"] == "sleep_study"
    assert row["category"] == "sleep"
    assert row["ahi"] == 27.3
    assert row["cpap_hours"] == 6.5
    assert row["mask_type"] == "nasal pillow"


def test_v1_tables_present_on_fresh_connect(tmp_project):
    """The five v1 fact tables get created by connect() via CREATE IF NOT
    EXISTS, so fresh test databases work without running alembic."""
    with storage.connect() as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {r[0] for r in cur.fetchall()}
    for required in (
        "daily_observations",
        "body_measurements",
        "medication_events",
        "clinical_events",
        "model_outputs",
    ):
        assert required in tables, f"{required} missing"
