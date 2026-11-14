from datetime import UTC, date, datetime

from backend.domain.planning import create_placement, get_planning, list_earlier_unfinished
from backend.domain.projects import create_project, rename_project
from backend.domain.tasks import create_task, set_task_completion
from backend.domain.weeks import close_week, preview_close


def test_earlier_unfinished_uses_current_leaves_and_all_saved_membership(db, client):
    project = create_project(db, "Original")
    parent = create_task(db, "Parent", project_id=project.id)
    leaf = create_task(db, "Leaf", parent_id=parent.id, project_id=project.id,
                       deadline="2026-12-01", estimate_minutes=45)
    done = create_task(db, "Done", project_id=project.id)
    today_task = create_task(db, "Today", project_id=project.id)
    future = create_task(db, "Future", project_id=project.id)
    for task in (leaf, done, today_task, future):
        create_placement(db, task.id, "2026-11-02")
    create_placement(db, leaf.id, "2026-11-03")
    set_task_completion(db, done.id, True)
    preview = preview_close(db, "2026-11-02")
    close_week(db, "2026-11-02", preview.preview_token)
    create_placement(db, today_task.id, "2026-11-14")
    create_placement(db, future.id, "2026-11-15")
    rename_project(db, project.id, "Current")

    before = client.get("/api/planning").json()
    rows = list_earlier_unfinished(db, date(2026, 11, 14))
    assert [row.model_dump(mode="json") for row in rows] == [{
        "id": leaf.id, "title": "Leaf", "project_id": project.id,
        "project_name": "Current", "parent_id": parent.id, "parent_title": "Parent",
        "last_planned_date": "2026-11-03", "deadline": "2026-12-01", "estimate_minutes": 45,
    }]
    assert client.get("/api/planning").json() == before


def test_planning_day_boundary_uses_service_timezone(db, client, monkeypatch):
    monkeypatch.setenv("BEARPLANS_TIMEZONE", "America/Los_Angeles")
    task = create_task(db, "Boundary")
    create_placement(db, task.id, "2026-11-14")
    before = get_planning(db, now=datetime(2026, 11, 15, 7, 59, tzinfo=UTC))
    after = get_planning(db, now=datetime(2026, 11, 15, 8, 0, tzinfo=UTC))
    assert before.today == date(2026, 11, 14) and before.earlier_unfinished == []
    assert after.today == date(2026, 11, 15)
    assert [row.id for row in after.earlier_unfinished] == [task.id]

    monkeypatch.setattr("backend.domain.planning.application_today", lambda now=None: (after.today, "America/Los_Angeles"))
    response = client.get("/api/planning", params={"week": "2026-10-01"})
    assert response.status_code == 200
    assert response.json()["today"] == "2026-11-15"
    assert response.json()["earlier_unfinished"][0]["id"] == task.id


def test_archived_membership_respects_current_parent_and_future_plans(db):
    parent = create_task(db, "Was a leaf")
    future = create_task(db, "Closed future")
    create_placement(db, parent.id, "2026-11-02")
    create_placement(db, future.id, "2026-11-02")
    preview = preview_close(db, "2026-11-02")
    close_week(db, "2026-11-02", preview.preview_token)
    create_task(db, "Child", parent_id=parent.id)
    create_placement(db, future.id, "2026-11-16")
    preview = preview_close(db, "2026-11-16")
    close_week(db, "2026-11-16", preview.preview_token)
    assert list_earlier_unfinished(db, date(2026, 11, 14)) == []
