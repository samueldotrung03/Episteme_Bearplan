"""HTTP boundary for atomic task capture, using disposable databases."""
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.domain.planning import list_placements
from backend.domain.tasks import list_tasks
from backend.domain.weeks import close_week, preview_close
from backend.storage.db import open_database


def test_capture_retry_survives_restart_and_conflicting_reuse(client, db):
    payload = {"operation_id": str(uuid4()), "title": "Study", "notes": "Read first", "deadline": "2099-11-20", "estimate_minutes": 30, "planned_date": "2026-11-11"}
    first = client.post("/api/task-captures", json=payload)
    assert first.status_code == 201
    result = first.json()
    assert result["task"]["title"] == "Study"
    assert result["placement"]["task_id"] == result["task"]["id"]
    assert result["placement"]["planned_date"] == payload["planned_date"]
    reopened = open_database(db.path)
    restarted = TestClient(create_app(reopened), base_url="http://127.0.0.1:8765")
    replay = restarted.post("/api/task-captures", json=payload)
    assert replay.status_code == 201 and replay.json() == result
    conflict = restarted.post("/api/task-captures", json={**payload, "title": "Different"})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["field"] == "operation_id"
    assert len(list_tasks(db)) == len(list_placements(db)) == 1


@pytest.mark.parametrize("change", [
    {"title": " "}, {"planned_date": "2026-02-30"}, {"estimate_minutes": True},
    {"operation_id": "not-a-uuid"}, {"unexpected": "value"},
])
def test_invalid_capture_does_not_write(client, db, change):
    response = client.post("/api/task-captures", json={"operation_id": str(uuid4()), "title": "Draft", "planned_date": "2026-11-11", **change})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"
    assert list_tasks(db) == [] and list_placements(db) == []


def test_closed_week_recovery_keeps_all_details_for_retry(client, db):
    close_week(db, "2026-11-09", preview_close(db, "2026-11-09").preview_token)
    payload = {"operation_id": str(uuid4()), "title": "Draft", "notes": "Keep me", "planned_date": "2026-11-11"}
    blocked = client.post("/api/task-captures", json=payload)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["field"] == "planned_date"
    assert list_tasks(db) == [] and list_placements(db) == []
    saved = client.post("/api/task-captures", json={**payload, "planned_date": "2026-11-18"})
    assert saved.status_code == 201
    assert saved.json()["task"]["notes"] == "Keep me"
    assert len(list_tasks(db)) == len(list_placements(db)) == 1


def test_storage_failure_rolls_back_and_retry_works(client, db, monkeypatch):
    import backend.domain.task_capture as capture
    original = capture._create_placement_tx
    def fail(*args):
        raise sqlite3.OperationalError("injected")
    monkeypatch.setattr(capture, "_create_placement_tx", fail)
    payload = {"operation_id": str(uuid4()), "title": "Retry", "planned_date": "2026-11-11"}
    failed = client.post("/api/task-captures", json=payload)
    assert failed.status_code == 503 and failed.json()["error"]["code"] == "storage_unavailable"
    assert list_tasks(db) == [] and list_placements(db) == []
    monkeypatch.setattr(capture, "_create_placement_tx", original)
    assert client.post("/api/task-captures", json=payload).status_code == 201
    assert len(list_tasks(db)) == len(list_placements(db)) == 1


def test_cross_origin_capture_is_rejected(client, db):
    response = client.post("/api/task-captures", json={"operation_id": str(uuid4()), "title": "Injected"}, headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "cross_origin"
    assert list_tasks(db) == []


def test_unscheduled_and_subtask_capture_preserve_existing_rules(client, db):
    parent = client.post("/api/tasks", json={"title": "Parent"}).json()
    result = client.post("/api/task-captures", json={"operation_id": str(uuid4()), "title": "Child", "parent_id": parent["id"]})
    assert result.status_code == 201
    assert result.json()["placement"] is None
    assert result.json()["task"]["parent_id"] == parent["id"]
    assert len(list_tasks(db)) == 2 and list_placements(db) == []
    child = result.json()["task"]
    rejected = client.post("/api/task-captures", json={"operation_id": str(uuid4()), "title": "Too deep", "parent_id": child["id"], "planned_date": "2026-11-11"})
    assert rejected.status_code == 422
    assert len(list_tasks(db)) == 2 and list_placements(db) == []


def test_replay_after_closure_returns_original_receipt(client, db):
    payload = {"operation_id": str(uuid4()), "title": "Recorded", "planned_date": "2026-11-11"}
    first = client.post("/api/task-captures", json=payload)
    assert first.status_code == 201
    close_week(db, "2026-11-09", preview_close(db, "2026-11-09").preview_token)
    replay = client.post("/api/task-captures", json=payload)
    assert replay.status_code == 201 and replay.json() == first.json()
    assert len(list_tasks(db)) == 1 and list_placements(db) == []
