"""Shared pytest fixtures for life-os-bridge tests."""

from pathlib import Path

import pytest

from src import config as cfg_mod


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Spin up a throwaway project ROOT with a writable config + empty health-log.

    Tests that exercise storage code should use this so they never touch the
    real config.yaml or the owner's health-log.md.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    sqlite_path = (project_root / "data.db").as_posix()
    health_log_path = (project_root / "health-log.md").as_posix()
    mental_health_log_path = (project_root / "mental-health-log.md").as_posix()
    (project_root / "config.yaml").write_text(
        "app:\n"
        "  host: 127.0.0.1\n"
        "  port: 5151\n"
        "  timezone: America/Chicago\n"
        "storage:\n"
        f"  sqlite_path: {sqlite_path}\n"
        f"  health_log_path: {health_log_path}\n"
        f"  mental_health_log_path: {mental_health_log_path}\n"
        "quiet_hours:\n"
        "  start: '22:00'\n"
        "  end: '07:00'\n"
        "wearable:\n"
        "  enabled_record_types:\n"
        "    - SleepSession\n"
        "    - RestingHeartRate\n"
        "    - OxygenSaturation\n"
        "    - Steps\n"
        "    - Weight\n",
        encoding="utf-8",
    )
    (project_root / "health-log.md").write_text("# Health Log\n", encoding="utf-8")
    (project_root / "mental-health-log.md").write_text("# Mental Health Log\n", encoding="utf-8")
    monkeypatch.setattr(cfg_mod, "ROOT", project_root)
    return project_root
