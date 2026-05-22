from datetime import date

from src.storage import upsert_health_log_field


def test_upsert_writes_to_today_when_no_target_date(tmp_project):
    upsert_health_log_field("Steps (prev day)", "4823 #bariatric #cardio")
    text = (tmp_project / "health-log.md").read_text(encoding="utf-8")
    today = date.today()
    assert f"## {today.isoformat()}, {today.strftime('%A')}" in text
    assert "**Steps (prev day):** 4823 #bariatric #cardio" in text


def test_upsert_writes_to_target_date_when_specified(tmp_project):
    target = date(2026, 5, 9)
    upsert_health_log_field("Steps (prev day)", "1205", target_date=target)
    text = (tmp_project / "health-log.md").read_text(encoding="utf-8")
    assert "## 2026-05-09, Saturday" in text
    assert "**Steps (prev day):** 1205" in text


def test_upsert_replaces_existing_field_on_target_date(tmp_project):
    target = date(2026, 5, 9)
    upsert_health_log_field("Steps (prev day)", "1000", target_date=target)
    upsert_health_log_field("Steps (prev day)", "1500", target_date=target)
    text = (tmp_project / "health-log.md").read_text(encoding="utf-8")
    assert "**Steps (prev day):** 1500" in text
    assert "**Steps (prev day):** 1000" not in text
