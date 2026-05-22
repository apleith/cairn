# Changelog

All notable changes to Cairn are recorded here. The format roughly follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and Cairn loosely
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once it
reaches v1.0. Until then, breaking changes between minor versions are
expected.

## [Unreleased]

### Unreleased changes since v0.1.0

- **Alembic migration scaffolding.** `alembic/` directory with `env.py`
  wired to `config.yaml`'s `storage.sqlite_path`, baseline revision
  `27e91b6ca1e5` (no-op, stamps the legacy `submissions` + `hc_*` tables
  as the starting point), and revision `2bd36a46271f` creating the five
  Cairn v1 fact tables: `daily_observations`, `body_measurements`,
  `medication_events`, `clinical_events`, `model_outputs`. The new
  tables sit alongside the legacy tables; nothing is dropped or rewritten
  yet. Standard `alembic upgrade head` applies.
- `alembic>=1.13` added to `requirements.txt`.
- `scripts/migrate_v0_to_v1.py` backfills `daily_observations` from the
  legacy `submissions` table. Migrates four `kind` values: `weight`,
  `bp`, `daily_health`, and `wearable` summary rows. The other two
  legacy kinds (`scale` mental-health responses and `reminder_fired`
  operational dedup) are intentionally not migrated. Idempotent via the
  `source='legacy_v0_*'` + `source_record_id=<submissions.id>` columns;
  re-runs require `--force` and rewrite cleanly. Snapshots the database
  before writing and writes a row-count report to `data/`.

- **Manual-entry routes for the three new fact tables.** `/measurements`
  writes to `body_measurements` (waist, hips, neck, upper arm, thigh + time
  of day + who measured). `/medications` writes to `medication_events` with
  generic name, dose, route, frequency, event_type (start / dose_change /
  pause / restart / stop / missed / refill), reason, and prescribing
  context; the numeric dose is auto-parsed from the dose string for the
  modeling layer. `/events` writes to `clinical_events` with category +
  certainty + optional sleep-study / CPAP fields. All three are linked
  from the home-page nav under a new "Periodic log" section.
- Storage helpers `save_body_measurement`, `save_medication_event`,
  `save_clinical_event`, and `save_daily_observation` in
  `src/storage.py` (a generic `_insert_fact` helper drops None values so
  SQLite defaults apply).
- **Mirror-write shim in `/weight`, `/bp`, and `/daily`.** Every POST to
  those handlers now writes the legacy `submissions` blob row AND a
  corresponding `daily_observations` row tagged
  `source='manual_form'` + `source_record_id='sub:<id>'`. The mirror
  closes the dual-write gap so the v1 schema receives every new entry
  going forward; modeling code can read from `daily_observations` alone.
  `/daily` translates its rich form (pill compliance, BM, edema, sleep
  hours+minutes, SpO2) into the corresponding `daily_observations`
  columns where they exist and into `notes` where they don't yet
  (SpO2 column is planned for v0.2).
- **`storage.SCHEMA` mirrors the Alembic v1 fact tables** with CREATE IF
  NOT EXISTS so fresh test databases pick them up without running an
  alembic upgrade. The Alembic revisions remain the authoritative source
  of truth for production deploys.
- **Test coverage for Phase 1 work** (`tests/test_v1_facts.py`,
  `tests/test_migration_v0_to_v1.py`): 17 new tests covering the five
  fact-table helpers, the four migration row-builders, the
  empty-row filter, and an end-to-end run of the migration script
  (dry-run, fresh apply, idempotency guard, --force re-run). Total
  suite: 55 passing.

### Planned for v0.2

- Segmented projection model with clinically plausible envelopes.
- Replace the remaining hardcoded paths in `src/food_log_writer.py` and
  `templates/today.html` with configurable values.
- First-party authentication for the Flask app (so Cairn is safe outside
  Tailscale).

## [0.1.0] — 2026-05-22

The first public release of Cairn. The project began life as
`life-os-bridge`, a private mobile health-logging companion to the author's
personal task system. It was extracted, sanitized, and relicensed under
Apache 2.0 for public sharing in the context of the GLP-1 and bariatric
patient communities, where a local-first, no-cloud, no-account journal that
respects validated screening instruments is in short supply.

### Added

- Apache 2.0 license and `NOTICE`.
- `NOT_MEDICAL_ADVICE.md`, `PRIVACY.md`, `SECURITY.md` to set expectations
  about clinical scope, data handling, and reporting paths.
- `config.example.yaml`, `busy-blocks.example.yaml`, `schedules.example.yaml`
  for new operators to copy.
- `pill_labels` block in `config.yaml` so the daily-entry medication labels
  are operator-configurable instead of hardcoded.
- Optional life-os integration: the `/today` dashboard now gracefully 404s
  if `integrations.life_os_scripts_path` is not configured, instead of
  failing to import at startup.

### Changed

- `setup-scheduler.ps1` now uses `$PSScriptRoot` instead of a hardcoded
  install path, so the scheduled task works wherever the repo lives.
- Stripped author-specific medication names from `templates/daily.html`.
  Pill labels are now driven by config.
- Stripped a Tailscale hostname reference from
  `populate_outlook_schedule.py` (the script is disabled in v0.1 anyway).

### Removed

- All pre-release commit history. The repository was reinitialized before
  the first public push because earlier commits referenced personal health
  measurements, real medication names, network topology, and recurring
  meeting schedules. The author retains a local archive of the prior
  history; it is not redistributable.

### Known limitations

- Some path defaults still assume the original author's filesystem layout.
  Specifically: `src/food_log_writer.py` and `templates/today.html`
  contain references to a `C:\life-os\` directory that other users will
  not have. These are functional bugs for new installs; they will be
  removed in v0.2.
- No first-party authentication on the Flask app. Deploy behind Tailscale
  or equivalent. See `SECURITY.md`.
- No CSRF protection on POST routes. Same threat-model assumption as above.
- The projection feature described in the README is planned, not shipped.
  v0.1 records data and prompts; v0.2 will add the projection model.
