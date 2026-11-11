"""Atomic task capture and durable replay use disposable databases."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from backend.domain.errors import InvalidInput
from backend.domain.planning import WeekConflict, list_placements
from backend.domain.task_capture import capture_task
from backend.domain.tasks import list_tasks
from backend.domain.weeks import close_week, preview_close
from backend.storage.db import open_database


def test_capture_replays_after_restart_without_duplicate(tmp_path):
    path = tmp_path / "capture.sqlite3"
    db = open_database(path)
    op = str(uuid4())
    original = capture_task(db, op, " Read notes ", planned_date="2026-11-11", estimate_minutes=30)
    replay = capture_task(open_database(path), op, "Read notes", planned_date="2026-11-11", estimate_minutes=30)
    assert replay == original
    assert len(list_tasks(db)) == 1
    assert len(list_placements(db)) == 1
    with pytest.raises(WeekConflict):
        capture_task(db, op, "Different", planned_date="2026-11-11", estimate_minutes=30)
    assert len(list_tasks(db)) == 1


def test_closed_week_and_failed_placement_roll_back_everything(db, monkeypatch):
    preview = preview_close(db, "2026-11-09")
    close_week(db, "2026-11-09", preview.preview_token)
    with pytest.raises(WeekConflict):
        capture_task(db, str(uuid4()), "Blocked", planned_date="2026-11-11")
    assert list_tasks(db) == []
    op = str(uuid4())
    import backend.domain.task_capture as capture
    original = capture._create_placement_tx
    def fail(*args):
        raise RuntimeError("simulated storage failure")
    monkeypatch.setattr(capture, "_create_placement_tx", fail)
    with pytest.raises(RuntimeError):
        capture_task(db, op, "Retry", planned_date="2026-11-18")
    assert list_tasks(db) == []
    monkeypatch.setattr(capture, "_create_placement_tx", original)
    assert capture_task(db, op, "Retry", planned_date="2026-11-18").placement is not None
    assert len(list_tasks(db)) == 1


def test_concurrent_retries_and_optional_date(db):
    op = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: capture_task(db, op, "No date"), range(2)))
    assert results[0] == results[1]
    assert results[0].placement is None
    assert len(list_tasks(db)) == 1
    with pytest.raises(InvalidInput):
        capture_task(db, "bad key", "Invalid")


def test_upgrade_from_schema_23_preserves_task_and_plan(tmp_path):
    from backend.domain.planning import create_placement
    from backend.domain.tasks import create_task
    from backend.storage.migrations import current_version

    path = tmp_path / "upgrade.sqlite3"
    db = open_database(path)
    task = create_task(db, "Existing task")
    placement = create_placement(db, task.id, "2026-11-11")
    # Construct a schema-23 fixture from this disposable database.
    with db.write() as conn:
        conn.execute("DROP TABLE task_capture_operations")
        conn.execute("DELETE FROM migration_fingerprints WHERE version = 24")
        conn.execute("DELETE FROM schema_migrations WHERE version = 24")
    upgraded = open_database(path)
    assert current_version(upgraded) == 24
    assert list_tasks(upgraded) == [task]
    assert list_placements(upgraded) == [placement]
    assert capture_task(upgraded, str(uuid4()), "New task").task.title == "New task"
