"""Weekly planning application functions shared by the UI and future adapters.

A leaf task may have distinct active planned dates, with at most one placement on
each date. Closed-week placements are archived separately. Tasks, completion and
deadlines are never cloned by scheduling. All task/placement/history reads in a
planning view share a SQLite read transaction.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timedelta
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from backend.domain.calendar import application_today
from backend.domain.errors import InvalidInput
from backend.domain.tasks import Task, _children_of, _list_tasks, _require_task
from backend.storage.db import Database, utc_now

_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class Placement(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    task_id: str
    planned_date: date
    # Optional local start time "HH:MM"; a timed placement becomes a Google Calendar event.
    start_time: str | None = None
    position: int | None = None
    created_at: datetime
    updated_at: datetime
    revision: int


class HistoricalTask(Task):
    project_name: str
    parent_title: str | None


class ClosedWeek(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_version: int = 1
    week_start: date
    week_end: date
    closed_at: datetime | None = None
    timezone: str
    tasks: list[HistoricalTask]
    placements: list[Placement]
    completed: int
    total: int


class ClosedWeekSummary(BaseModel):
    week_start: date
    week_end: date
    closed_at: datetime
    completed: int
    total: int


class EarlierUnfinishedTask(BaseModel):
    id: str
    title: str
    project_id: str
    project_name: str
    parent_id: str | None
    parent_title: str | None
    last_planned_date: date
    deadline: date | None
    estimate_minutes: int | None


class PlanningSnapshot(BaseModel):
    today: date
    timezone: str
    week_start: date
    week_end: date
    tasks: list[Task]
    placements: list[Placement]
    earlier_unfinished: list[EarlierUnfinishedTask] = []
    closed_week: ClosedWeek | None = None
    closed_weeks: list[ClosedWeekSummary] = []


class WeekConflict(InvalidInput):
    """A closed week or a changed reviewed state prevents this operation."""


class PlacementConflict(InvalidInput):
    def __init__(self, planned_date: str) -> None:
        super().__init__(
            "planned_date",
            f"This task is already planned for {planned_date}. Choose another day. "
            "All existing placements were kept; nothing was changed.",
        )


class PlacementOrderConflict(InvalidInput):
    def __init__(self) -> None:
        super().__init__("order", "This day's plan changed. Refresh the plan and try again; nothing was changed.")


def _date(value: object, field: str = "planned_date") -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise InvalidInput(field, "Use a real date in YYYY-MM-DD form.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise InvalidInput(field, "Use a real date in YYYY-MM-DD form.") from None


def week_bounds(value: str | date) -> tuple[date, date]:
    """Normalize any date to its Monday–Sunday calendar week, without time arithmetic."""
    day = _date(value, "week")
    try:
        monday = day - timedelta(days=day.weekday())
        return monday, monday + timedelta(days=6)
    except OverflowError:
        raise InvalidInput("week", "That week is outside the supported calendar range.") from None


def _select(conn: sqlite3.Connection) -> str:
    """Placements with their optional start time. Before migration 18 (legacy-upgrade
    paths run current code on older schemas) there are no start times."""
    has_times = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'placement_times'").fetchone()
    has_positions = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'placement_positions'").fetchone()
    return ("SELECT p.*, " + ("t.start_time" if has_times else "NULL AS start_time")
            + ", " + ("pos.position" if has_positions else "NULL AS position") + " FROM planned_items p"
            + (" LEFT JOIN placement_times t ON t.placement_id = p.id" if has_times else "")
            + (" LEFT JOIN placement_positions pos ON pos.placement_id = p.id" if has_positions else ""))


def _placement(row: sqlite3.Row) -> Placement:
    return Placement(**dict(row))


def _require_placement(conn: sqlite3.Connection, placement_id: object) -> sqlite3.Row:
    if not isinstance(placement_id, str):
        raise InvalidInput("placement_id", "Placement id must be text.")
    row = conn.execute(_select(conn) + " WHERE p.id = ?", (placement_id,)).fetchone()
    if row is None:
        archived = conn.execute("SELECT week_start FROM closed_placements WHERE id = ?", (placement_id,)).fetchone()
        if archived:
            raise WeekConflict(
                "placement_id", f"This placement belongs to the closed week starting {archived['week_start']}. "
                "Historical placements are read-only. Plan the current task in an open week instead.",
            )
        raise InvalidInput("placement_id", "This planned placement no longer exists. Refresh the plan.")
    return row


def _list_placements(conn: sqlite3.Connection) -> list[Placement]:
    return [_placement(row) for row in conn.execute(
        _select(conn) + " ORDER BY p.planned_date, position, p.created_at, p.rowid"
    ).fetchall()]


def list_placements(db: Database) -> list[Placement]:
    with db.read() as conn:
        return _list_placements(conn)


def _earlier_unfinished(conn: sqlite3.Connection, today: date) -> list[EarlierUnfinishedTask]:
    rows = conn.execute(
        """WITH membership AS (
               SELECT task_id, planned_date FROM planned_items
               UNION ALL
               SELECT task_id, planned_date FROM closed_placements
           ), latest AS (
               SELECT task_id, MAX(planned_date) AS last_planned_date
               FROM membership GROUP BY task_id
           )
           SELECT t.id, t.title, t.project_id, p.name AS project_name,
                  t.parent_id, parent.title AS parent_title, latest.last_planned_date,
                  t.deadline, t.estimate_minutes
           FROM latest JOIN tasks t ON t.id = latest.task_id
           JOIN projects p ON p.id = t.project_id
           LEFT JOIN tasks parent ON parent.id = t.parent_id
           WHERE latest.last_planned_date < ? AND t.completed_at IS NULL
             AND NOT EXISTS (SELECT 1 FROM tasks child WHERE child.parent_id = t.id)
           ORDER BY latest.last_planned_date DESC, t.title COLLATE NOCASE, t.id""",
        (today.isoformat(),),
    ).fetchall()
    return [EarlierUnfinishedTask(**dict(row)) for row in rows]


def list_earlier_unfinished(db: Database, today: date) -> list[EarlierUnfinishedTask]:
    """Current incomplete leaves whose latest saved placement predates today."""
    with db.read() as conn:
        return _earlier_unfinished(conn, _date(today, "today"))


def get_planning(db: Database, week: str | date | None = None, *, now: datetime | None = None) -> PlanningSnapshot:
    from backend.domain.weeks import _closed_week, _closed_week_summaries

    today, timezone = application_today(now)
    monday, sunday = week_bounds(today if week is None else week)
    with db.read() as conn:
        conn.execute("BEGIN")
        return PlanningSnapshot(
            today=today, timezone=timezone, week_start=monday, week_end=sunday,
            tasks=_list_tasks(conn), placements=_list_placements(conn),
            earlier_unfinished=_earlier_unfinished(conn, today),
            closed_week=_closed_week(conn, monday.isoformat()),
            closed_weeks=_closed_week_summaries(conn),
        )


def _planned_date(value: object) -> str:
    day = _date(value)
    week_bounds(day)  # Every saved placement must have a representable full week.
    return day.isoformat()


def _require_leaf(conn: sqlite3.Connection, task_id: object) -> None:
    _require_task(conn, task_id)
    if _children_of(conn, task_id):
        raise InvalidInput("task_id", "Plan this task's subtasks instead. Parent tasks are shown as context.")


def _require_open_week(conn: sqlite3.Connection, day: str) -> None:
    monday, _ = week_bounds(day)
    if conn.execute("SELECT 1 FROM closed_weeks WHERE week_start = ?", (monday.isoformat(),)).fetchone():
        raise WeekConflict(
            "planned_date", f"The week starting {monday.isoformat()} is closed. "
            "Historical placements are read-only. Choose an open week; reopening is not available.",
        )


def _check_already_planned(conn: sqlite3.Connection, task_id: str, day: str, *, except_id: str = "") -> None:
    existing = conn.execute(
        "SELECT planned_date FROM planned_items WHERE task_id = ? AND planned_date = ? AND id <> ?",
        (task_id, day, except_id),
    ).fetchone()
    if existing:
        raise PlacementConflict(existing["planned_date"])


def create_placement(
    db: Database, task_id: str, planned_date: str | date, *, source_placement_id: str | None = None,
) -> Placement:
    day = _planned_date(planned_date)
    with db.write() as conn:
        if source_placement_id is not None:
            source = _require_placement(conn, source_placement_id)
            _require_open_week(conn, source["planned_date"])
            if source["task_id"] != task_id:
                raise InvalidInput("source_placement_id", "The source placement belongs to a different task. Refresh the plan; nothing was changed.")
        return _create_placement_tx(conn, task_id, day)


def _create_placement_tx(conn: sqlite3.Connection, task_id: str, planned_date: str | date) -> Placement:
    """create_placement inside a caller's write transaction (shared with assistant actions)."""
    day = _planned_date(planned_date)
    now = utc_now()
    placement_id = str(uuid4())
    _require_open_week(conn, day)
    _require_leaf(conn, task_id)
    _check_already_planned(conn, task_id, day)
    conn.execute(
        "INSERT INTO planned_items (id, task_id, planned_date, created_at, updated_at, revision) "
        "VALUES (?, ?, ?, ?, ?, 1)",
        (placement_id, task_id, day, now, now),
    )
    if _append_position(conn, placement_id, day) is not None:
        return _placement(_require_placement(conn, placement_id))
    # Built from what was written (a new placement has no start time), so this also
    # works on older schemas that legacy-upgrade tests build with current code.
    return Placement(id=placement_id, task_id=task_id, planned_date=day, created_at=now, updated_at=now, revision=1)


def _append_position(conn: sqlite3.Connection, placement_id: str, day: str) -> int | None:
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'placement_positions'").fetchone():
        return None
    position = conn.execute(
        "SELECT COALESCE(MAX(pos.position), -1) + 1 FROM planned_items p "
        "JOIN placement_positions pos ON pos.placement_id = p.id WHERE p.planned_date = ?", (day,),
    ).fetchone()[0]
    conn.execute("INSERT INTO placement_positions VALUES (?, ?)", (placement_id, position))
    return position


def move_placement(db: Database, placement_id: str, planned_date: str | date) -> Placement:
    day = _planned_date(planned_date)
    with db.write() as conn:
        row = _require_placement(conn, placement_id)
        _require_open_week(conn, row["planned_date"])
        _require_open_week(conn, day)
        _require_leaf(conn, row["task_id"])
        _check_already_planned(conn, row["task_id"], day, except_id=placement_id)
        if row["planned_date"] != day:
            old_day = row["planned_date"]
            conn.execute(
                "UPDATE planned_items SET planned_date = ?, updated_at = ?, revision = revision + 1 WHERE id = ?",
                (day, utc_now(), placement_id),
            )
            if row["position"] is not None:
                source = [r["id"] for r in _day_order(conn, old_day)]
                destination = [r["id"] for r in _day_order(conn, day) if r["id"] != placement_id]
                _save_order(conn, source)
                _save_order(conn, [*destination, placement_id])
        return _placement(_require_placement(conn, placement_id))


def _day_order(conn: sqlite3.Connection, day: str) -> list[sqlite3.Row]:
    return conn.execute(_select(conn) + " WHERE p.planned_date = ? ORDER BY position, p.created_at, p.rowid", (day,)).fetchall()


def _save_order(conn: sqlite3.Connection, ids: list[str]) -> None:
    conn.executemany("UPDATE placement_positions SET position = ? WHERE placement_id = ?",
                     [(position, placement_id) for position, placement_id in enumerate(ids)])


def reorder_placement(db: Database, placement_id: str, planned_date: str | date, position: int,
                      source_order: list[tuple[str, int]], destination_order: list[tuple[str, int]]) -> Placement:
    """Move within or between days only if both reviewed day orders still match."""
    day = _planned_date(planned_date)
    if isinstance(position, bool) or not isinstance(position, int) or position < 0:
        raise InvalidInput("position", "Choose a non-negative position in the destination day.")
    with db.write() as conn:
        row = _require_placement(conn, placement_id)
        source_day = row["planned_date"]
        _require_open_week(conn, source_day)
        _require_open_week(conn, day)
        source = _day_order(conn, source_day)
        destination = source if day == source_day else _day_order(conn, day)
        def signature(items: list[sqlite3.Row]) -> list[tuple[str, int]]:
            return [(item["id"], item["revision"]) for item in items]
        if signature(source) != source_order or signature(destination) != destination_order:
            raise PlacementOrderConflict()
        _check_already_planned(conn, row["task_id"], day, except_id=placement_id)
        remaining = [item["id"] for item in destination if item["id"] != placement_id]
        if position > len(remaining):
            raise InvalidInput("position", "Choose a position within the destination day.")
        remaining.insert(position, placement_id)
        if day == source_day and remaining == [item["id"] for item in source]:
            return _placement(row)
        conn.execute("UPDATE planned_items SET planned_date = ?, updated_at = ?, revision = revision + 1 WHERE id = ?",
                     (day, utc_now(), placement_id))
        if day != source_day:
            _save_order(conn, [item["id"] for item in source if item["id"] != placement_id])
        _save_order(conn, remaining)
        return _placement(_require_placement(conn, placement_id))


_TIME = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]")


def set_placement_time(db: Database, placement_id: str, start_time: str | None) -> Placement:
    """Set or clear a placement's optional start time ("HH:MM", 24-hour, local)."""
    if start_time is not None and (not isinstance(start_time, str) or not _TIME.fullmatch(start_time)):
        raise InvalidInput("start_time", "Start time must look like 14:30 (24-hour), or be empty.")
    with db.write() as conn:
        row = _require_placement(conn, placement_id)
        _require_open_week(conn, row["planned_date"])
        if row["start_time"] != start_time:
            if start_time is None:
                conn.execute("DELETE FROM placement_times WHERE placement_id = ?", (placement_id,))
            else:
                conn.execute(
                    "INSERT INTO placement_times (placement_id, start_time) VALUES (?, ?) "
                    "ON CONFLICT(placement_id) DO UPDATE SET start_time = excluded.start_time",
                    (placement_id, start_time),
                )
            conn.execute(
                "UPDATE planned_items SET updated_at = ?, revision = revision + 1 WHERE id = ?",
                (utc_now(), placement_id),
            )
        return _placement(_require_placement(conn, placement_id))


def remove_placement(db: Database, placement_id: str) -> str:
    with db.write() as conn:
        _remove_placement_tx(conn, placement_id)
    return placement_id


def _remove_placement_tx(conn: sqlite3.Connection, placement_id: str) -> sqlite3.Row:
    """remove_placement inside a caller's write transaction; returns the removed row."""
    row = _require_placement(conn, placement_id)
    _require_open_week(conn, row["planned_date"])
    conn.execute("DELETE FROM planned_items WHERE id = ?", (placement_id,))
    if row["position"] is not None:
        _save_order(conn, [item["id"] for item in _day_order(conn, row["planned_date"])])
    return row
