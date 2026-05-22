import json
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import ROOT, load

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    subkind TEXT,
    submitted_at TEXT NOT NULL,
    score REAL,
    band TEXT,
    data_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_submissions_kind ON submissions(kind, submitted_at);

-- Health Connect raw record tables. One per record type.
-- hc_record_uid is HC's own UUID; UNIQUE so INSERT OR IGNORE is idempotent.
-- source_app and source_device come from each HC record's metadata.

CREATE TABLE IF NOT EXISTS hc_sleep_session (
    hc_record_uid TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    title TEXT,
    notes TEXT,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hc_sleep_session_start ON hc_sleep_session(start_time);

CREATE TABLE IF NOT EXISTS hc_sleep_stage (
    hc_record_uid TEXT PRIMARY KEY,
    session_uid TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    stage TEXT NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hc_sleep_stage_session ON hc_sleep_stage(session_uid);

CREATE TABLE IF NOT EXISTS hc_heart_rate (
    hc_record_uid TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    bpm INTEGER NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hc_hr_time ON hc_heart_rate(time);

CREATE TABLE IF NOT EXISTS hc_resting_heart_rate (
    hc_record_uid TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    bpm INTEGER NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hc_rhr_time ON hc_resting_heart_rate(time);

CREATE TABLE IF NOT EXISTS hc_heart_rate_variability (
    hc_record_uid TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    rmssd_ms REAL NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hc_hrv_time ON hc_heart_rate_variability(time);

CREATE TABLE IF NOT EXISTS hc_oxygen_saturation (
    hc_record_uid TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    spo2_pct REAL NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hc_spo2_time ON hc_oxygen_saturation(time);

CREATE TABLE IF NOT EXISTS hc_steps (
    hc_record_uid TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    count INTEGER NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hc_steps_start ON hc_steps(start_time);

CREATE TABLE IF NOT EXISTS hc_distance (
    hc_record_uid TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    meters REAL NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hc_floors_climbed (
    hc_record_uid TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    floors REAL NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hc_active_calories (
    hc_record_uid TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    kcal REAL NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hc_total_calories (
    hc_record_uid TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    kcal REAL NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hc_exercise_session (
    hc_record_uid TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    exercise_type TEXT NOT NULL,
    title TEXT,
    notes TEXT,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hc_exercise_session_start ON hc_exercise_session(start_time);

CREATE TABLE IF NOT EXISTS hc_respiratory_rate (
    hc_record_uid TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    breaths_per_minute REAL NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hc_weight (
    hc_record_uid TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    weight_kg REAL NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hc_weight_time ON hc_weight(time);

CREATE TABLE IF NOT EXISTS hc_body_fat (
    hc_record_uid TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    percentage REAL NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hc_lean_body_mass (
    hc_record_uid TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    mass_kg REAL NOT NULL,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hc_blood_pressure (
    hc_record_uid TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    systolic INTEGER NOT NULL,
    diastolic INTEGER NOT NULL,
    pulse_bpm INTEGER,
    source_app TEXT,
    source_device TEXT,
    synced_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hc_bp_time ON hc_blood_pressure(time);

-- Cairn v1 fact tables (kept in sync with alembic/versions/2bd36a46271f).
-- CREATE IF NOT EXISTS so fresh test databases get them without running
-- the alembic upgrade. Production deploys still run alembic upgrade head.

CREATE TABLE IF NOT EXISTS daily_observations (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    time TIME,
    weight_lb REAL,
    weight_observed BOOLEAN,
    weight_source TEXT,
    weight_context TEXT,
    weight_confidence TEXT,
    systolic INTEGER,
    diastolic INTEGER,
    pulse_from_bp_device INTEGER,
    bp_posture TEXT,
    resting_hr INTEGER,
    average_hr INTEGER,
    max_hr INTEGER,
    steps INTEGER,
    steps_observed BOOLEAN,
    device_worn BOOLEAN,
    active_minutes INTEGER,
    distance_miles REAL,
    exercise_minutes INTEGER,
    resistance_training BOOLEAN,
    protein_g REAL,
    protein_logged BOOLEAN,
    calories REAL,
    carbs_g REAL,
    fat_g REAL,
    fluids_oz REAL,
    sleep_hours REAL,
    source TEXT NOT NULL,
    import_timestamp DATETIME NOT NULL DEFAULT (datetime('now')),
    source_file TEXT,
    source_record_id TEXT,
    timezone TEXT,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_daily_observations_date ON daily_observations(date);
CREATE INDEX IF NOT EXISTS idx_daily_observations_source ON daily_observations(source);

CREATE TABLE IF NOT EXISTS body_measurements (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    waist_in REAL,
    hips_in REAL,
    neck_in REAL,
    upper_arm_in REAL,
    thigh_in REAL,
    measurement_time TEXT,
    measurement_method TEXT,
    source TEXT NOT NULL,
    import_timestamp DATETIME NOT NULL DEFAULT (datetime('now')),
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_body_measurements_date ON body_measurements(date);

CREATE TABLE IF NOT EXISTS medication_events (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    medication_name TEXT NOT NULL,
    generic_name TEXT,
    dose TEXT,
    dose_numeric REAL,
    dose_unit TEXT,
    route TEXT,
    frequency TEXT,
    event_type TEXT NOT NULL,
    reason TEXT,
    prescribing_context TEXT,
    source TEXT NOT NULL,
    import_timestamp DATETIME NOT NULL DEFAULT (datetime('now')),
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_medication_events_date ON medication_events(date);
CREATE INDEX IF NOT EXISTS idx_medication_events_name ON medication_events(medication_name);

CREATE TABLE IF NOT EXISTS clinical_events (
    id INTEGER PRIMARY KEY,
    event_id TEXT UNIQUE,
    date DATE NOT NULL,
    event_type TEXT NOT NULL,
    category TEXT NOT NULL,
    label TEXT NOT NULL,
    certainty TEXT,
    source TEXT NOT NULL,
    ahi REAL,
    cpap_pressure TEXT,
    cpap_hours REAL,
    mask_type TEXT,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_clinical_events_date ON clinical_events(date);
CREATE INDEX IF NOT EXISTS idx_clinical_events_category ON clinical_events(category);

CREATE TABLE IF NOT EXISTS model_outputs (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    day INTEGER NOT NULL,
    trend_weight_lb REAL,
    trend_method TEXT,
    expected_weight_lb REAL,
    lower_plausible_weight_lb REAL,
    upper_plausible_weight_lb REAL,
    pct_twl REAL,
    pct_ewl REAL,
    bmi REAL,
    phase TEXT,
    segment_id TEXT,
    model_version TEXT NOT NULL,
    generated_at DATETIME NOT NULL DEFAULT (datetime('now')),
    markers TEXT
);
CREATE INDEX IF NOT EXISTS idx_model_outputs_date ON model_outputs(date);
"""


def db_path() -> Path:
    return ROOT / load()["storage"]["sqlite_path"]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_submission(kind: str, data: dict, subkind: str = None, score: float = None, band: str = None) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO submissions (kind, subkind, submitted_at, score, band, data_json) VALUES (?, ?, ?, ?, ?, ?)",
            (kind, subkind, datetime.now().isoformat(timespec="seconds"), score, band, json.dumps(data)),
        )
        return cur.lastrowid


def _insert_fact(table: str, row: dict) -> int:
    """Generic INSERT into one of the v1 fact tables. None values are dropped
    so SQLite uses the column default where applicable."""
    payload = {k: v for k, v in row.items() if v is not None}
    cols = list(payload.keys())
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    with connect() as conn:
        cur = conn.execute(sql, [payload[c] for c in cols])
        return cur.lastrowid


def save_daily_observation(row: dict) -> int:
    """Insert a row into daily_observations. `row` must include `date` and
    `source`. Any subset of the measurement columns may be populated; None
    values are dropped so SQLite uses column defaults where applicable."""
    return _insert_fact("daily_observations", row)


def save_body_measurement(row: dict) -> int:
    """Insert a row into body_measurements. `row` must include `date` and
    `source`; any of waist_in/hips_in/neck_in/upper_arm_in/thigh_in may be
    present. measurement_time and measurement_method are optional."""
    return _insert_fact("body_measurements", row)


def save_medication_event(row: dict) -> int:
    """Insert a row into medication_events. `row` must include `date`,
    `medication_name`, `event_type`, and `source`."""
    return _insert_fact("medication_events", row)


def save_clinical_event(row: dict) -> int:
    """Insert a row into clinical_events. `row` must include `date`,
    `event_type`, `category`, `label`, and `source`."""
    return _insert_fact("clinical_events", row)


def last_submission(kind: str, subkind: str = None) -> dict | None:
    with connect() as conn:
        if subkind:
            row = conn.execute(
                "SELECT * FROM submissions WHERE kind=? AND subkind=? ORDER BY submitted_at DESC LIMIT 1",
                (kind, subkind),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM submissions WHERE kind=? ORDER BY submitted_at DESC LIMIT 1",
                (kind,),
            ).fetchone()
        return dict(row) if row else None


def submissions_today(kind: str) -> int:
    today_iso = date.today().isoformat()
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM submissions WHERE kind=? AND submitted_at LIKE ?",
            (kind, today_iso + "%"),
        ).fetchone()
        return row["c"] if row else 0


# ---- Markdown mirrors ----

def _section_header(d: date) -> str:
    return f"## {d.isoformat()}, {d.strftime('%A')}"


def _today_header() -> str:
    return _section_header(date.today())


def upsert_health_log_field(field: str, value: str, target_date: date | None = None) -> None:
    """Find target_date's section in health-log.md; update field or create section.

    target_date defaults to today. Pass a past date for backfill writes.
    """
    path = Path(load()["storage"]["health_log_path"])
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    header = _section_header(target_date) if target_date else _today_header()

    if header in text:
        section_pattern = re.compile(
            rf"({re.escape(header)}.*?)(?=\n## |\Z)", re.DOTALL
        )
        match = section_pattern.search(text)
        section = match.group(1)

        field_pattern = re.compile(rf"^\- \*\*{re.escape(field)}:\*\* .*$", re.MULTILINE)
        new_line = f"- **{field}:** {value}"
        if field_pattern.search(section):
            new_section = field_pattern.sub(new_line, section, count=1)
        else:
            new_section = section.rstrip() + f"\n{new_line}\n"
        text = text.replace(section, new_section, 1)
    else:
        # Stub schema must match personal/health/health-log.md
        # (objective-only as of 2026-05-09; 4-slot pill schema as of 2026-05-17).
        new_section = (
            f"\n{header}\n\n"
            f"- **Wake:** —\n"
            f"- **Breakfast:** —\n"
            f"- **Lunch:** —\n"
            f"- **Bedtime:** —\n"
            f"- **Weight:** —\n"
            f"- **BP:** —\n"
            f"- **Sleep (wearable):** —\n"
            f"- **Resting HR:** —\n"
            f"- **SpO2 (overnight low):** —\n"
            f"- **Steps (prev day):** —\n"
            f"- **BM:** —\n"
            f"- **Edema:** —\n"
            f"- **Note:** —\n"
        )
        new_section = new_section.replace(f"- **{field}:** —", f"- **{field}:** {value}")
        insertion_point = text.find("\n## ")
        if insertion_point == -1:
            text = text.rstrip() + "\n" + new_section if text else new_section.lstrip()
        else:
            text = text[:insertion_point] + "\n" + new_section + text[insertion_point:]

    path.write_text(text, encoding="utf-8")


SCREEN_CADENCE_DAYS = 14  # WHO-5/PHQ-9/GAD-7/ISI all reflect "past 2 weeks"


def screen_cadence(scale_ids: list[str]) -> list[dict]:
    """For each scale_id, return cadence metadata: last taken, next due, days
    until due, and a status flag ('due' | 'soon' | 'later' | 'never').

    Used by the index + /today dashboard to surface a countdown and a
    visible 'take this now' flag every 14 days.
    """
    today_d = date.today()
    out = []
    with connect() as conn:
        for sid in scale_ids:
            row = conn.execute(
                "SELECT MAX(submitted_at) AS last FROM submissions WHERE kind='scale' AND subkind=?",
                (sid,),
            ).fetchone()
            last_iso = row["last"] if row else None
            if not last_iso:
                out.append({
                    "scale_id": sid,
                    "last": None,
                    "next_due": today_d.isoformat(),
                    "days_until": 0,
                    "status": "never",
                })
                continue
            last_d = date.fromisoformat(last_iso[:10])
            next_due = last_d + timedelta(days=SCREEN_CADENCE_DAYS)
            days_until = (next_due - today_d).days
            if days_until <= 0:
                status = "due"
            elif days_until <= 2:
                status = "soon"
            else:
                status = "later"
            out.append({
                "scale_id": sid,
                "last": last_d.isoformat(),
                "next_due": next_due.isoformat(),
                "days_until": days_until,
                "status": status,
            })
    return out


def read_recent_weights(limit: int = 1) -> list[tuple[str, float]]:
    """Return the most recent N (date_iso, weight_lb) tuples from health-log.md.

    health-log.md is the canonical store; the SQLite submissions table only
    captures weights submitted THROUGH the bridge, which misses any weight
    typed directly into the markdown by Obsidian, terminal-Claude, voice, etc.
    """
    path = Path(load()["storage"]["health_log_path"])
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")

    date_re = re.compile(r"^## (\d{4}-\d{2}-\d{2})", re.MULTILINE)
    weight_re = re.compile(r"^- \*\*Weight:\*\*\s*([0-9]+(?:\.[0-9]+)?)", re.MULTILINE)

    # Walk through every date section in document order. Most-recent-first
    # in the file is conventional but not guaranteed; we sort at the end.
    results: list[tuple[str, float]] = []
    matches = list(date_re.finditer(text))
    for i, m in enumerate(matches):
        date_iso = m.group(1)
        section_start = m.end()
        section_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section = text[section_start:section_end]
        wm = weight_re.search(section)
        if wm:
            try:
                results.append((date_iso, float(wm.group(1))))
            except ValueError:
                continue

    # Sort newest first, return up to `limit`.
    results.sort(key=lambda r: r[0], reverse=True)
    return results[:limit]


def append_mental_health_log(entry: str) -> None:
    path = Path(load()["storage"]["mental_health_log_path"])
    header = "# Mental Health Log\n\n> Append-only. Written by life-os-bridge. Structured entries for later analysis.\n\n---\n"
    if not path.exists():
        path.write_text(header, encoding="utf-8")
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + entry.rstrip() + "\n")


def append_activity_log(activity: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    append_mental_health_log(f"## Activity — {ts}\n\n- **Done:** {activity}\n")


# ---- HC raw record writes ----

_HC_INSERTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "SleepSession": (
        "INSERT OR IGNORE INTO hc_sleep_session "
        "(hc_record_uid, start_time, end_time, title, notes, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "start_time", "end_time", "title", "notes", "source_app", "source_device"),
    ),
    "SleepStage": (
        "INSERT OR IGNORE INTO hc_sleep_stage "
        "(hc_record_uid, session_uid, start_time, end_time, stage, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "session_uid", "start_time", "end_time", "stage", "source_app", "source_device"),
    ),
    "HeartRate": (
        "INSERT OR IGNORE INTO hc_heart_rate "
        "(hc_record_uid, time, bpm, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "time", "bpm", "source_app", "source_device"),
    ),
    "RestingHeartRate": (
        "INSERT OR IGNORE INTO hc_resting_heart_rate "
        "(hc_record_uid, time, bpm, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "time", "bpm", "source_app", "source_device"),
    ),
    "HeartRateVariabilityRmssd": (
        "INSERT OR IGNORE INTO hc_heart_rate_variability "
        "(hc_record_uid, time, rmssd_ms, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "time", "rmssd_ms", "source_app", "source_device"),
    ),
    "OxygenSaturation": (
        "INSERT OR IGNORE INTO hc_oxygen_saturation "
        "(hc_record_uid, time, spo2_pct, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "time", "spo2_pct", "source_app", "source_device"),
    ),
    "Steps": (
        "INSERT OR IGNORE INTO hc_steps "
        "(hc_record_uid, start_time, end_time, count, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "start_time", "end_time", "count", "source_app", "source_device"),
    ),
    "Distance": (
        "INSERT OR IGNORE INTO hc_distance "
        "(hc_record_uid, start_time, end_time, meters, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "start_time", "end_time", "meters", "source_app", "source_device"),
    ),
    "FloorsClimbed": (
        "INSERT OR IGNORE INTO hc_floors_climbed "
        "(hc_record_uid, start_time, end_time, floors, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "start_time", "end_time", "floors", "source_app", "source_device"),
    ),
    "ActiveCaloriesBurned": (
        "INSERT OR IGNORE INTO hc_active_calories "
        "(hc_record_uid, start_time, end_time, kcal, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "start_time", "end_time", "kcal", "source_app", "source_device"),
    ),
    "TotalCaloriesBurned": (
        "INSERT OR IGNORE INTO hc_total_calories "
        "(hc_record_uid, start_time, end_time, kcal, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "start_time", "end_time", "kcal", "source_app", "source_device"),
    ),
    "ExerciseSession": (
        "INSERT OR IGNORE INTO hc_exercise_session "
        "(hc_record_uid, start_time, end_time, exercise_type, title, notes, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "start_time", "end_time", "exercise_type", "title", "notes", "source_app", "source_device"),
    ),
    "RespiratoryRate": (
        "INSERT OR IGNORE INTO hc_respiratory_rate "
        "(hc_record_uid, time, breaths_per_minute, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "time", "breaths_per_minute", "source_app", "source_device"),
    ),
    "Weight": (
        "INSERT OR IGNORE INTO hc_weight "
        "(hc_record_uid, time, weight_kg, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "time", "weight_kg", "source_app", "source_device"),
    ),
    "BodyFat": (
        "INSERT OR IGNORE INTO hc_body_fat "
        "(hc_record_uid, time, percentage, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "time", "percentage", "source_app", "source_device"),
    ),
    "LeanBodyMass": (
        "INSERT OR IGNORE INTO hc_lean_body_mass "
        "(hc_record_uid, time, mass_kg, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "time", "mass_kg", "source_app", "source_device"),
    ),
    "BloodPressure": (
        "INSERT OR IGNORE INTO hc_blood_pressure "
        "(hc_record_uid, time, systolic, diastolic, pulse_bpm, source_app, source_device, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("hc_record_uid", "time", "systolic", "diastolic", "pulse_bpm", "source_app", "source_device"),
    ),
}


def insert_hc_record(record: dict, conn: sqlite3.Connection | None = None) -> bool:
    """Insert one HC record into the appropriate raw table. Returns True if
    a new row was inserted, False if hc_record_uid already existed.
    Raises ValueError for an unknown record_type.

    If `conn` is provided, reuse it (caller manages lifecycle). Otherwise
    open a fresh connection per call. Bulk callers (e.g. /wearable/bulk
    with thousands of records on first-sync backfill) MUST pass a shared
    conn: connection open + schema rerun per row otherwise turns a 5000-
    record backfill into a 30-90 second wait.
    """
    rtype = record.get("record_type")
    if rtype not in _HC_INSERTS:
        raise ValueError(f"unknown record type: {rtype}")
    sql, field_order = _HC_INSERTS[rtype]
    values = tuple(record.get(f) for f in field_order) + (datetime.now().isoformat(timespec="seconds"),)
    if conn is not None:
        cur = conn.execute(sql, values)
        return cur.rowcount > 0
    with connect() as owned:
        cur = owned.execute(sql, values)
        return cur.rowcount > 0
