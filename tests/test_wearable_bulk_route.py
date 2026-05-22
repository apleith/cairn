import pytest

import app as flask_app


@pytest.fixture
def client(tmp_project):
    flask_app.app.config["TESTING"] = True
    return flask_app.app.test_client()


def test_bulk_inserts_records_and_summarizes(client, tmp_project):
    payload = {
        "records": [
            {
                "record_type": "RestingHeartRate",
                "hc_record_uid": "rhr-1",
                "time": "2026-05-11T07:30:00",
                "bpm": 62,
                "source_app": "com.samsung.health",
                "source_device": "Galaxy Fit 3",
            },
            {
                "record_type": "Steps",
                "hc_record_uid": "steps-1",
                "start_time": "2026-05-10T08:00:00",
                "end_time": "2026-05-10T20:00:00",
                "count": 4200,
                "source_app": "com.samsung.health",
                "source_device": "Galaxy Fit 3",
            },
        ]
    }
    res = client.post("/wearable/bulk", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert data["counts"]["RestingHeartRate"] == 1
    assert data["counts"]["Steps"] == 1
    assert "2026-05-11" in data["dates_summarized"]

    text = (tmp_project / "health-log.md").read_text(encoding="utf-8")
    assert "**Resting HR:** 62 bpm #cardio" in text
    assert "**Steps (prev day):** 4200" in text


def test_bulk_dedupes_repeated_uids(client, tmp_project):
    payload = {
        "records": [
            {
                "record_type": "RestingHeartRate",
                "hc_record_uid": "rhr-1",
                "time": "2026-05-11T07:30:00",
                "bpm": 62,
                "source_app": "com.samsung.health",
                "source_device": "Galaxy Fit 3",
            },
        ]
    }
    r1 = client.post("/wearable/bulk", json=payload).get_json()
    r2 = client.post("/wearable/bulk", json=payload).get_json()
    assert r1["counts"]["RestingHeartRate"] == 1
    assert r2["counts"]["RestingHeartRate"] == 0


def test_bulk_rejects_non_json(client, tmp_project):
    res = client.post("/wearable/bulk", data="not json", content_type="text/plain")
    assert res.status_code == 400


def test_bulk_skips_unknown_record_types_without_failing_batch(client, tmp_project):
    payload = {
        "records": [
            {"record_type": "NotARealType", "hc_record_uid": "x"},
            {
                "record_type": "RestingHeartRate",
                "hc_record_uid": "rhr-1",
                "time": "2026-05-11T07:30:00",
                "bpm": 62,
                "source_app": "com.samsung.health",
                "source_device": "Galaxy Fit 3",
            },
        ]
    }
    res = client.post("/wearable/bulk", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["counts"]["RestingHeartRate"] == 1
    assert "NotARealType" in data["skipped_types"]


def test_bulk_summarizes_every_touched_date(client, tmp_project):
    payload = {
        "records": [
            {
                "record_type": "RestingHeartRate", "hc_record_uid": "rhr-1",
                "time": "2026-05-09T07:30:00", "bpm": 60,
                "source_app": "x", "source_device": "y",
            },
            {
                "record_type": "RestingHeartRate", "hc_record_uid": "rhr-2",
                "time": "2026-05-10T07:30:00", "bpm": 61,
                "source_app": "x", "source_device": "y",
            },
            {
                "record_type": "RestingHeartRate", "hc_record_uid": "rhr-3",
                "time": "2026-05-11T07:30:00", "bpm": 62,
                "source_app": "x", "source_device": "y",
            },
        ]
    }
    res = client.post("/wearable/bulk", json=payload).get_json()
    assert set(res["dates_summarized"]) == {"2026-05-09", "2026-05-10", "2026-05-11"}
