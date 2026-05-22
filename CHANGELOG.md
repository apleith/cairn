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

### Planned for v0.2

- `scripts/migrate_v0_to_v1.py` to backfill `daily_observations` from
  the existing `submissions` table (weight, BP, daily-health entries).
- Manual-entry routes and PWA forms for `body_measurements`,
  `medication_events`, and `clinical_events`.
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
