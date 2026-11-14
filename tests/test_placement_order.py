import pytest
from uuid import uuid4

from backend.domain.planning import create_placement, list_placements, set_placement_time
from backend.domain.tasks import create_task
from backend.domain.weeks import apply_carryover, close_week, preview_carryover, preview_close
from backend.storage.db import Database, open_database
from backend.storage.migrations import Migration, MigrationError, current_version, load_migrations, migrate
from tests.conftest import Service, free_port, http_json


def signature(rows, day):
    return [{"id": row.id, "revision": row.revision} for row in rows if row.planned_date.isoformat() == day]


def request(client, placement, day, position, source, destination):
    return client.put(f"/api/placements/{placement.id}/order", json={
        "planned_date": day, "position": position, "source_order": source, "destination_order": destination,
    })


def test_order_move_timed_task_stale_delete_and_restart(db, client):
    a, b, c, d = [create_task(db, title) for title in "ABCD"]
    a, b, c = [create_placement(db, task.id, "2026-11-09") for task in (a, b, c)]
    d = create_placement(db, d.id, "2026-11-10")
    b = set_placement_time(db, b.id, "09:30")
    rows = list_placements(db)
    before = signature(rows, "2026-11-09")
    result = request(client, c, "2026-11-09", 0, before, before)
    assert result.status_code == 200 and result.json()["position"] == 0
    rows = list_placements(db)
    assert [row.id for row in rows] == [c.id, a.id, b.id, d.id]
    assert request(client, a, "2026-11-09", 0, before, before).json()["error"]["code"] == "placement_order_conflict"
    current = signature(rows, "2026-11-09")
    assert request(client, c, "2026-11-09", 0, current, current).json()["revision"] == result.json()["revision"]
    moved = request(client, b, "2026-11-10", 0, current, signature(rows, "2026-11-10"))
    assert moved.status_code == 200 and moved.json()["start_time"] == "09:30"
    assert [(row.id, row.position) for row in list_placements(db)] == [(c.id, 0), (a.id, 1), (b.id, 0), (d.id, 1)]
    assert client.delete(f"/api/placements/{c.id}").status_code == 200
    assert [(row.id, row.position) for row in list_placements(open_database(db.path))] == [(a.id, 0), (b.id, 0), (d.id, 1)]
    assert client.patch(f"/api/placements/{a.id}", json={"planned_date": "2026-11-10"}).json()["position"] == 2


def test_closed_week_snapshot_order_and_rejection(db, client):
    a, b = [create_placement(db, create_task(db, title).id, "2026-11-09") for title in ("A", "B")]
    rows = list_placements(db)
    current = signature(rows, "2026-11-09")
    assert request(client, b, "2026-11-09", 0, current, current).status_code == 200
    closed = close_week(db, "2026-11-09", preview_close(db, "2026-11-09").preview_token)
    assert [p.id for p in closed.placements] == [b.id, a.id]
    result = request(client, b, "2026-11-09", 0, [], [])
    assert result.status_code == 409 and result.json()["error"]["code"] == "week_conflict"
    assert client.get("/api/planning", params={"week": "2026-11-09"}).json()["closed_week"]["placements"][0]["id"] == b.id


def test_cross_day_conflict_and_stale_destination_do_not_change_either_day(db, client):
    task = create_task(db, "Same task")
    source = create_placement(db, task.id, "2026-11-09")
    create_placement(db, task.id, "2026-11-10")
    rows = list_placements(db)
    s, d = signature(rows, "2026-11-09"), signature(rows, "2026-11-10")
    result = request(client, source, "2026-11-10", 0, s, d)
    assert result.status_code == 409 and result.json()["error"]["code"] == "placement_conflict"
    assert list_placements(db) == rows
    other = create_placement(db, create_task(db, "Other").id, "2026-11-09")
    before = list_placements(db)
    result = request(client, other, "2026-11-10", 0, signature(before, "2026-11-09"), [])
    assert result.status_code == 409 and result.json()["error"]["code"] == "placement_order_conflict"
    assert list_placements(db) == before


def test_carryover_appends_after_existing_placements_and_replays(db):
    task = create_task(db, "Carry")
    create_placement(db, task.id, "2026-11-09")
    close_week(db, "2026-11-09", preview_close(db, "2026-11-09").preview_token)
    existing = create_placement(db, create_task(db, "Existing").id, "2026-11-16")
    selected = [{"task_id": task.id, "planned_date": "2026-11-16"}]
    preview = preview_carryover(db, "2026-11-09", selected)
    operation = str(uuid4())
    result = apply_carryover(db, "2026-11-09", selected, preview.preview_token, operation)
    assert result.placements[0].position == 1
    assert [(p.id, p.position) for p in list_placements(db)] == [(existing.id, 0), (result.placements[0].id, 1)]
    assert apply_carryover(db, "2026-11-09", selected, preview.preview_token, operation) == result


def test_schema25_upgrade_and_failed_migration_retry(tmp_path):
    db = Database(tmp_path / "upgrade.sqlite")
    migrations = load_migrations()
    migrate(db, migrations[:25])
    tasks = [create_task(db, title) for title in ("A", "B", "C")]
    placements = [create_placement(db, task.id, "2026-11-09") for task in tasks]
    with db.read() as conn:
        before = [tuple(row) for row in conn.execute("SELECT * FROM planned_items ORDER BY created_at, rowid")]
    broken = Migration(26, migrations[25].name, migrations[25].sql + "\nINSERT INTO missing_table VALUES (1);")
    with pytest.raises(MigrationError, match="rolled back"):
        migrate(db, [*migrations[:25], broken])
    assert current_version(db) == 25
    with db.read() as conn:
        assert [tuple(row) for row in conn.execute("SELECT * FROM planned_items ORDER BY created_at, rowid")] == before
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'placement_positions'").fetchone()
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    migrate(db)
    reopened = open_database(db.path)
    with reopened.read() as conn:
        assert [tuple(row) for row in conn.execute("SELECT * FROM planned_items ORDER BY created_at, rowid")] == before
    assert [(p.id, p.position) for p in list_placements(reopened)] == [(p.id, i) for i, p in enumerate(placements)]


def test_order_survives_service_restart(tmp_path):
    data_dir = tmp_path / "service-data"
    service = Service(data_dir, free_port()).start()
    try:
        task_ids = [http_json("POST", service.url + "/api/tasks", {"title": title})[1]["id"] for title in ("A", "B")]
        placements = [http_json("POST", service.url + "/api/placements", {"task_id": task_id, "planned_date": "2026-11-09"})[1]
                      for task_id in task_ids]
        entries = [{"id": item["id"], "revision": item["revision"]} for item in placements]
        status, _ = http_json("PUT", service.url + f"/api/placements/{placements[1]['id']}/order", {
            "planned_date": "2026-11-09", "position": 0, "source_order": entries, "destination_order": entries,
        })
        assert status == 200
        assert service.stop() == 0
        service = Service(data_dir, service.port).start()
        status, plan = http_json("GET", service.url + "/api/planning")
        assert status == 200
        assert [(item["id"], item["position"]) for item in plan["placements"]] == [
            (placements[1]["id"], 0), (placements[0]["id"], 1),
        ]
    finally:
        service.kill()
