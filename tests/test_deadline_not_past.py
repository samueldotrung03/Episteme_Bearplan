"""A-03: a newly entered or changed deadline may not be before today (today is allowed)."""
from datetime import timedelta
from uuid import uuid4

from backend.domain.calendar import application_today
from backend.domain.task_capture import capture_task
from backend.domain.tasks import create_task, get_task


def _days(offset: int) -> str:
    return (application_today()[0] + timedelta(days=offset)).isoformat()


def test_task_api_rejects_a_past_deadline_and_allows_today(client, db):
    past = client.post("/api/tasks", json={"title": "Late", "deadline": _days(-1)})
    assert past.status_code == 422 and "before today" in past.text
    assert client.get("/api/tasks").json()["tasks"] == []
    assert client.post("/api/tasks", json={"title": "Now", "deadline": _days(0)}).status_code == 201


def test_editing_keeps_a_stored_overdue_deadline_but_rejects_a_new_past_one(client, db):
    stored = create_task(db, "Overdue", deadline=_days(-10))  # entered earlier, or imported
    rename = client.patch(f"/api/tasks/{stored.id}", json={"title": "Overdue essay", "deadline": _days(-10)})
    assert rename.status_code == 200 and rename.json()["deadline"] == _days(-10)
    changed = client.patch(f"/api/tasks/{stored.id}", json={"deadline": _days(-3)})
    assert changed.status_code == 422 and str(get_task(db, stored.id).deadline) == _days(-10)
    assert client.patch(f"/api/tasks/{stored.id}", json={"deadline": _days(0)}).status_code == 200
    assert client.patch(f"/api/tasks/{stored.id}", json={"deadline": None}).status_code == 200


def test_task_capture_rejects_a_past_deadline_but_replays_an_earlier_save(client, db):
    past = client.post("/api/task-captures", json={"operation_id": str(uuid4()), "title": "Late", "deadline": _days(-1)})
    assert past.status_code == 422 and "before today" in past.text
    # Saved when that deadline was today; the retry the next day still returns the saved result.
    op = str(uuid4())
    original = capture_task(db, op, "Saved yesterday", deadline=_days(-1))
    retry = client.post("/api/task-captures", json={"operation_id": op, "title": "Saved yesterday", "deadline": _days(-1)})
    assert retry.status_code == 201 and retry.json()["task"]["id"] == original.task.id
