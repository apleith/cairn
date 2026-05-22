"""Tests for scripts/migrate_v0_to_v1.py.

Exercises the four kind-specific row builders directly (pure functions),
then drives the full main() flow via subprocess against a throwaway
database to verify idempotency, --force, and --dry-run.
"""
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from scripts import migrate_v0_to_v1 as M


def test_row_from_weight():
    row = M._row_from_weight(
        sub_id=1,
        submitted_at="2026-04-17T08:00:00",
        data={"weight_lb": 624.0, "note": "after coffee"},
    )
    assert row["date"] == "2026-04-17"
    assert row["weight_lb"] == 624.0
    assert row["weight_source"] == "manual"
    assert row["weight_observed"] is True
    assert row["notes"] == "after coffee"
    assert row["source"] == "legacy_v0_weight"
    assert row["source_record_id"] == "1"


def test_row_from_weight_no_note():
    row = M._row_from_weight(
        sub_id=2,
        submitted_at="2026-04-18T07:30:00",
        data={"weight_lb": 627.0, "note": ""},
    )
    assert row["weight_lb"] == 627.0
    assert row["notes"] is None


def test_row_from_bp_parses_strings():
    row = M._row_from_bp(
        sub_id=99,
        submitted_at="2026-05-09T10:52:54",
        data={"systolic": "128", "diastolic": "82", "pulse": "68"},
    )
    assert row["systolic"] == 128
    assert row["diastolic"] == 82
    assert row["pulse_from_bp_device"] == 68


def test_row_from_daily_health_parses_bp_string():
    row = M._row_from_daily_health(
        sub_id=42,
        submitted_at="2026-05-09T11:33:52",
        data={
            "weight": "624.4",
            "bp": "128/82",
            "resting_hr": "62",
            "sleep_wearable": "7.2",
            "steps_prev": "4823",
            "wake": "Y",
            "breakfast": "Y",
            "bedtime": "",
            "bm": "Y",
            "edema": "N",
            "note": "tired today",
        },
    )
    assert row["weight_lb"] == 624.4
    assert row["systolic"] == 128
    assert row["diastolic"] == 82
    assert row["resting_hr"] == 62
    assert row["sleep_hours"] == 7.2
    assert row["steps"] == 4823
    # Notes capture pill-Y/bm/edema-N/free-text. Empty pill slots are skipped.
    assert "wake=Y" in row["notes"]
    assert "breakfast=Y" in row["notes"]
    assert "bedtime" not in row["notes"]
    assert "bm=Y" in row["notes"]
    assert "edema=N" in row["notes"]
    assert "tired today" in row["notes"]


def test_row_from_daily_health_bad_bp_string():
    row = M._row_from_daily_health(
        sub_id=43,
        submitted_at="2026-05-09T11:33:52",
        data={"bp": "not a bp"},
    )
    assert row["systolic"] is None
    assert row["diastolic"] is None


def test_row_from_wearable_uses_data_date():
    row = M._row_from_wearable(
        sub_id=100,
        submitted_at="2026-05-11T07:44:20",
        data={"date": "2026-05-10", "steps_prev_day": 4823},
    )
    assert row["date"] == "2026-05-10"
    assert row["steps"] == 4823
    assert row["steps_observed"] is True
    assert row["source"] == "legacy_v0_wearable_summary"


def test_row_keys_present_filters_empty():
    """A row with only date+source+source_record_id and no payload must
    NOT be inserted (would create a pointless empty observation)."""
    empty = {"date": "2026-05-22", "source": "legacy_v0_weight",
             "source_record_id": "1"}
    assert M._row_keys_present(empty) is False
    populated = {**empty, "weight_lb": 620.0}
    assert M._row_keys_present(populated) is True


# ---------------- end-to-end via subprocess ----------------

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def fake_project(tmp_path):
    """A throwaway project root that mirrors the live tree just enough to
    drive scripts/migrate_v0_to_v1.py through `python -m scripts.migrate_v0_to_v1`.

    Copies the scripts/ package plus an empty data.db pre-populated with
    legacy `submissions` rows AND the daily_observations table the script
    targets.
    """
    project = tmp_path / "cairn"
    project.mkdir()
    # Copy scripts/ package
    shutil.copytree(ROOT / "scripts", project / "scripts")
    # Stripped-down config.yaml
    (project / "config.yaml").write_text(
        "storage:\n  sqlite_path: data.db\n",
        encoding="utf-8",
    )
    # Pre-seed data.db with the legacy + new schemas + sample rows
    db = project / "data.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            subkind TEXT,
            submitted_at TEXT NOT NULL,
            score REAL,
            band TEXT,
            data_json TEXT NOT NULL
        );
        CREATE TABLE daily_observations (
            id INTEGER PRIMARY KEY,
            date DATE NOT NULL,
            weight_lb REAL,
            weight_observed BOOLEAN,
            weight_source TEXT,
            systolic INTEGER,
            diastolic INTEGER,
            pulse_from_bp_device INTEGER,
            resting_hr INTEGER,
            steps INTEGER,
            steps_observed BOOLEAN,
            device_worn BOOLEAN,
            sleep_hours REAL,
            source TEXT NOT NULL,
            import_timestamp DATETIME NOT NULL DEFAULT (datetime('now')),
            source_record_id TEXT,
            notes TEXT
        );
    """)
    conn.executemany(
        "INSERT INTO submissions (kind, subkind, submitted_at, data_json) VALUES (?, ?, ?, ?)",
        [
            ("weight", None, "2026-04-17T08:00:00",
             json.dumps({"weight_lb": 624.0, "note": "after coffee"})),
            ("bp", None, "2026-05-09T10:52:54",
             json.dumps({"systolic": "128", "diastolic": "82", "pulse": "68"})),
            ("reminder_fired", "meds_am_6", "2026-05-09T06:01:00",
             json.dumps({"reminder_id": "meds_am_6", "critical": True})),
            ("scale", "phq9", "2026-05-09T15:00:00",
             json.dumps({"responses": [1, 2, 3]})),
            ("wearable", "2026-05-10", "2026-05-10T07:00:00",
             json.dumps({"date": "2026-05-10", "steps_prev_day": 4823})),
        ],
    )
    conn.commit()
    conn.close()
    return project


def _run(project, *args):
    """Invoke the migration script via `python -m scripts.migrate_v0_to_v1`."""
    return subprocess.run(
        [sys.executable, "-m", "scripts.migrate_v0_to_v1", *args],
        cwd=str(project),
        capture_output=True,
        text=True,
    )


def _count_legacy_rows(project):
    conn = sqlite3.connect(project / "data.db")
    n = conn.execute(
        "SELECT COUNT(*) FROM daily_observations WHERE source LIKE 'legacy_v0_%'"
    ).fetchone()[0]
    conn.close()
    return n


def test_migration_dry_run_writes_nothing(fake_project):
    result = _run(fake_project, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert "DRY-RUN" in result.stdout
    assert _count_legacy_rows(fake_project) == 0


def test_migration_inserts_expected_rows(fake_project):
    result = _run(fake_project)
    assert result.returncode == 0, result.stderr
    # 1 weight + 1 bp + 1 wearable = 3 rows. scale and reminder_fired are skipped.
    assert _count_legacy_rows(fake_project) == 3
    # Snapshot was written
    snapshots = list(fake_project.glob("data.db.snapshot-pre-migrate-*"))
    assert len(snapshots) == 1
    # Migration report exists
    reports = list((fake_project / "data").glob("migration-report-*.txt"))
    assert len(reports) == 1


def test_migration_idempotent_without_force(fake_project):
    assert _run(fake_project).returncode == 0
    second = _run(fake_project)
    assert second.returncode == 3
    assert "already exist" in second.stderr
    assert _count_legacy_rows(fake_project) == 3  # unchanged


def test_migration_force_wipes_and_redoes(fake_project):
    assert _run(fake_project).returncode == 0
    forced = _run(fake_project, "--force")
    assert forced.returncode == 0, forced.stderr
    assert "Deleted 3 prior legacy_v0_* row(s)" in forced.stdout
    assert _count_legacy_rows(fake_project) == 3  # same count after rewrite
