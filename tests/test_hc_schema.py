from src.storage import connect

EXPECTED_TABLES = {
    "hc_sleep_session",
    "hc_sleep_stage",
    "hc_heart_rate",
    "hc_resting_heart_rate",
    "hc_heart_rate_variability",
    "hc_oxygen_saturation",
    "hc_steps",
    "hc_distance",
    "hc_floors_climbed",
    "hc_active_calories",
    "hc_total_calories",
    "hc_exercise_session",
    "hc_respiratory_rate",
    "hc_weight",
    "hc_body_fat",
    "hc_lean_body_mass",
    "hc_blood_pressure",
}


def test_all_hc_tables_created(tmp_project):
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'hc_%'"
        ).fetchall()
    names = {r["name"] for r in rows}
    assert EXPECTED_TABLES.issubset(names), f"missing: {EXPECTED_TABLES - names}"


def test_hc_record_uid_is_unique(tmp_project):
    with connect() as conn:
        conn.execute(
            "INSERT INTO hc_steps (hc_record_uid, start_time, end_time, count, source_app, source_device, synced_at) "
            "VALUES ('uid-1', '2026-05-11T00:00:00', '2026-05-11T01:00:00', 305, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-11T08:00:00')"
        )
        conn.execute(
            "INSERT OR IGNORE INTO hc_steps (hc_record_uid, start_time, end_time, count, source_app, source_device, synced_at) "
            "VALUES ('uid-1', '2026-05-11T00:00:00', '2026-05-11T01:00:00', 305, 'com.samsung.health', 'Galaxy Fit 3', '2026-05-11T08:00:00')"
        )
        n = conn.execute("SELECT COUNT(*) AS c FROM hc_steps").fetchone()["c"]
    assert n == 1
