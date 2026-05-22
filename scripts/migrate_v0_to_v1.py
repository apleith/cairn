"""Backfill the Cairn v1 daily_observations fact table from the legacy
v0 submissions table.

Maps four legacy `submissions.kind` values onto daily_observations rows:

    weight        -> one row carrying weight_lb + notes
    bp            -> one row carrying systolic, diastolic, pulse_from_bp_device
    daily_health  -> one row with whichever fields were filled
                     (weight, systolic, diastolic, resting_hr, sleep_hours,
                     steps, plus pill compliance + bm + edema captured in notes)
    wearable      -> one row carrying steps from the daily HC summary

The other two legacy kinds are intentionally NOT migrated:

    scale            screening responses don't fit the v1 fact tables yet;
                     they remain in submissions until a mental_health_screens
                     table lands.
    reminder_fired   operational dedup log, not health data.

The script is idempotent: every inserted row carries source='legacy_v0_<kind>'
and source_record_id=<submissions.id>. A subsequent run aborts unless --force
is passed; with --force, previously migrated rows are deleted and rewritten so
re-runs converge.

Snapshots data.db to data.db.snapshot-pre-migrate-v0-to-v1-<timestamp> before
writing anything (also skipped with --dry-run).

Usage:
    python -m scripts.migrate_v0_to_v1                   # apply
    python -m scripts.migrate_v0_to_v1 --dry-run         # preview only
    python -m scripts.migrate_v0_to_v1 --force           # re-run, wipe + redo
"""
import argparse
import json
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _sqlite_path() -> Path:
    cfg_path = ROOT / "config.yaml"
    if cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        sqlite_rel = (cfg.get("storage") or {}).get("sqlite_path") or "data.db"
    else:
        sqlite_rel = "data.db"
    return (ROOT / sqlite_rel).resolve()


def _isodate(submitted_at: str) -> str:
    return submitted_at[:10]


def _parse_int(value) -> int | None:
    if value in (None, "", "None"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def _parse_float(value) -> float | None:
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


_BP_RE = re.compile(r"^\s*(\d{2,3})\s*/\s*(\d{2,3})\s*$")


def _parse_bp_string(value) -> tuple[int | None, int | None]:
    """daily_health stores BP as a single string like '128/82'."""
    if not value:
        return None, None
    m = _BP_RE.match(str(value))
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def _row_from_weight(sub_id: int, submitted_at: str, data: dict) -> dict:
    return {
        "date": _isodate(submitted_at),
        "weight_lb": _parse_float(data.get("weight_lb")),
        "weight_observed": True,
        "weight_source": "manual",
        "source": "legacy_v0_weight",
        "source_record_id": str(sub_id),
        "notes": (data.get("note") or None) or None,
    }


def _row_from_bp(sub_id: int, submitted_at: str, data: dict) -> dict:
    return {
        "date": _isodate(submitted_at),
        "systolic": _parse_int(data.get("systolic")),
        "diastolic": _parse_int(data.get("diastolic")),
        "pulse_from_bp_device": _parse_int(data.get("pulse")),
        "source": "legacy_v0_bp",
        "source_record_id": str(sub_id),
    }


def _row_from_daily_health(sub_id: int, submitted_at: str, data: dict) -> dict:
    systolic, diastolic = _parse_bp_string(data.get("bp"))
    notes_parts: list[str] = []
    for label, key in (("wake", "wake"), ("breakfast", "breakfast"), ("bedtime", "bedtime"),
                       ("bm", "bm"), ("edema", "edema")):
        v = data.get(key)
        if v:
            notes_parts.append(f"{label}={v}")
    free_note = (data.get("note") or "").strip()
    if free_note:
        notes_parts.append(free_note)
    return {
        "date": _isodate(submitted_at),
        "weight_lb": _parse_float(data.get("weight")),
        "weight_observed": bool(data.get("weight")),
        "weight_source": "manual" if data.get("weight") else None,
        "systolic": systolic,
        "diastolic": diastolic,
        "resting_hr": _parse_int(data.get("resting_hr")),
        "sleep_hours": _parse_float(data.get("sleep_wearable")),
        "steps": _parse_int(data.get("steps_prev")),
        "source": "legacy_v0_daily_health",
        "source_record_id": str(sub_id),
        "notes": "; ".join(notes_parts) if notes_parts else None,
    }


def _row_from_wearable(sub_id: int, submitted_at: str, data: dict) -> dict:
    date = data.get("date") or _isodate(submitted_at)
    return {
        "date": date,
        "steps": _parse_int(data.get("steps_prev_day")),
        "steps_observed": True,
        "device_worn": True,
        "source": "legacy_v0_wearable_summary",
        "source_record_id": str(sub_id),
    }


KIND_TO_BUILDER = {
    "weight": _row_from_weight,
    "bp": _row_from_bp,
    "daily_health": _row_from_daily_health,
    "wearable": _row_from_wearable,
}


def _row_keys_present(row: dict) -> bool:
    """Skip empty rows where nothing useful made it through."""
    payload_keys = {k for k in row.keys() if k not in ("date", "source", "source_record_id")}
    return any(row.get(k) is not None for k in payload_keys)


def _insert_row(conn: sqlite3.Connection, row: dict) -> None:
    cols = list(row.keys())
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT INTO daily_observations ({', '.join(cols)}) VALUES ({placeholders})"
    conn.execute(sql, [row[c] for c in cols])


def _snapshot(db: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = db.with_name(f"{db.name}.snapshot-pre-migrate-v0-to-v1-{ts}")
    shutil.copy2(db, dst)
    return dst


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan, write nothing.")
    parser.add_argument("--force", action="store_true",
                        help="If migration rows already exist, wipe them and rewrite.")
    args = parser.parse_args(argv)

    db = _sqlite_path()
    if not db.exists():
        print(f"error: database not found at {db}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM daily_observations WHERE source LIKE 'legacy_v0_%'"
    )
    existing = cur.fetchone()[0]
    if existing and not args.force and not args.dry_run:
        print(f"error: {existing} legacy_v0_* rows already exist in "
              "daily_observations. Pass --force to delete and re-migrate, "
              "or --dry-run to preview.", file=sys.stderr)
        return 3

    cur.execute(
        "SELECT id, kind, submitted_at, data_json FROM submissions "
        "WHERE kind IN ('weight', 'bp', 'daily_health', 'wearable') "
        "ORDER BY submitted_at"
    )
    candidates = cur.fetchall()

    rows: list[dict] = []
    skipped: list[tuple[int, str, str]] = []
    for sub in candidates:
        try:
            data = json.loads(sub["data_json"]) if sub["data_json"] else {}
        except json.JSONDecodeError:
            skipped.append((sub["id"], sub["kind"], "bad json"))
            continue
        builder = KIND_TO_BUILDER[sub["kind"]]
        row = builder(sub["id"], sub["submitted_at"], data)
        if not _row_keys_present(row):
            skipped.append((sub["id"], sub["kind"], "no fields populated"))
            continue
        rows.append(row)

    print(f"Source DB:           {db}")
    print(f"Existing legacy_v0_* rows in daily_observations: {existing}")
    print(f"Candidate submissions: {len(candidates)}")
    print(f"Will migrate:          {len(rows)}")
    print(f"Will skip (empty/bad): {len(skipped)}")
    print()
    by_source: dict[str, int] = {}
    for r in rows:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
    for src, n in sorted(by_source.items()):
        print(f"  {src:32} {n}")
    if skipped:
        print()
        print("Skipped rows:")
        for sid, kind, reason in skipped:
            print(f"  submissions.id={sid:>4} kind={kind:<14} {reason}")

    if args.dry_run:
        print()
        print("DRY-RUN: no changes written.")
        return 0

    snap = _snapshot(db)
    print()
    print(f"Snapshot written:    {snap}")

    try:
        with conn:
            if args.force and existing:
                cur.execute(
                    "DELETE FROM daily_observations WHERE source LIKE 'legacy_v0_%'"
                )
                print(f"Deleted {cur.rowcount} prior legacy_v0_* row(s).")
            for row in rows:
                _insert_row(conn, row)
    except sqlite3.Error as e:
        print(f"error during migration: {e}", file=sys.stderr)
        return 4

    cur.execute(
        "SELECT COUNT(*) FROM daily_observations WHERE source LIKE 'legacy_v0_%'"
    )
    after = cur.fetchone()[0]
    print(f"Inserted:            {len(rows)} rows")
    print(f"Total legacy_v0_* in daily_observations now: {after}")

    report_dir = ROOT / "data"
    report_dir.mkdir(exist_ok=True)
    report = report_dir / f"migration-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"Cairn v0 -> v1 migration report\n")
        f.write(f"Generated:           {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"Database:            {db}\n")
        f.write(f"Snapshot:            {snap}\n")
        f.write(f"Existing before:     {existing}\n")
        f.write(f"Candidates:          {len(candidates)}\n")
        f.write(f"Migrated:            {len(rows)}\n")
        f.write(f"Skipped:             {len(skipped)}\n")
        f.write(f"\nBy source:\n")
        for src, n in sorted(by_source.items()):
            f.write(f"  {src:32} {n}\n")
        if skipped:
            f.write("\nSkipped:\n")
            for sid, kind, reason in skipped:
                f.write(f"  submissions.id={sid} kind={kind} reason={reason}\n")
    print(f"Report written:      {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
