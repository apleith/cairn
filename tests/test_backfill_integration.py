"""Integration tests: multi-date backfill via /wearable/bulk.

Verifies that posting a 3-day batch of HC records:
  1. Writes all expected fields to health-log.md for each covered date.
  2. Is fully idempotent: a second identical POST inserts 0 rows and still
     summarizes the same set of dates.
"""

import json
from pathlib import Path

import pytest

import app as flask_app


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "backfill_sample.json"


@pytest.fixture
def client(tmp_project):
    flask_app.app.config["TESTING"] = True
    return flask_app.app.test_client()


def test_three_day_backfill_writes_all_dates(client, tmp_project):
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    res = client.post("/wearable/bulk", json=payload).get_json()
    assert res["ok"] is True

    assert set(res["dates_summarized"]) >= {"2026-05-08", "2026-05-09", "2026-05-10", "2026-05-11"}

    text = (tmp_project / "health-log.md").read_text(encoding="utf-8")

    assert "## 2026-05-09, Saturday" in text
    assert "**Sleep (wearable):** 8h 0m" in text
    assert "**Resting HR:** 60 bpm" in text
    assert "**SpO2 (overnight low):** 93%" in text
    assert "**Steps (prev day):** 1200" in text

    assert "## 2026-05-11, Monday" in text
    assert "**Weight:** 615.3" in text
    assert "**Steps (prev day):** 4500" in text
    assert "**SpO2 (overnight low):** 92%" in text


def test_replaying_the_same_batch_is_idempotent(client, tmp_project):
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    r1 = client.post("/wearable/bulk", json=payload).get_json()
    r2 = client.post("/wearable/bulk", json=payload).get_json()

    assert sum(r1["counts"].values()) == len(payload["records"])
    assert sum(r2["counts"].values()) == 0
    assert set(r2["dates_summarized"]) == set(r1["dates_summarized"])
