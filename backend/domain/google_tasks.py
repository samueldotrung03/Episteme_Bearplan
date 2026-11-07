"""Google Tasks sync: BearPlans -> Google, plus completion ticked in Google.

Each sync also updates Google Calendar events (see google_calendar.py).

User decisions (2026-11-02):
- Every project, task and subtask syncs. Project -> task list named like the project,
  task -> task, subtask -> subtask (both sides allow one level only).
- BearPlans is the source of truth. Titles, notes, dates, nesting and completion are
  sent to Google; an edit made in Google to those is overwritten on the next sync.
  The exception: ticking (or unticking) a task in Google changes its completion in
  BearPlans, unless BearPlans also changed that completion since the last sync.
- Google's date is the deadline if set, else the next planned day (or the latest
  past one), else none. Google Tasks only keeps a date.
- BearPlans touches only the lists and tasks it created (remembered in google_* tables).
  Tasks the user adds in Google, and their own lists, are left alone.

Network calls happen outside transactions. An unresolved create blocks sync
until explicitly reviewed, including when the provider response is lost.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypeVar

from pydantic import BaseModel

from backend.domain.calendar import application_today
from backend.domain.google_calendar import CalendarClient, sync_calendar
from backend.domain.google_create_intents import PendingCreate, begin, pending_for, publish, require_clear, returned_id, review_key as create_review_key
from backend.domain.google_account import account_review_key, check_account
from backend.domain.google_reading import read_calendars
from backend.domain.tasks import Task, _list_tasks, _set_completion_tx
from backend.storage.db import Database, utc_now

_LOG = logging.getLogger("bearplans.google")
PERIOD_SECONDS = 120
NUDGE_DELAY_SECONDS = 4
NOTES_LIMIT = 8000
_Result = TypeVar("_Result")


class TasksClient(Protocol):
    def lists(self) -> list[dict[str, Any]]: ...
    def insert_list(self, title: str) -> dict[str, Any]: ...
    def rename_list(self, list_id: str, title: str) -> dict[str, Any]: ...
    def tasks(self, list_id: str) -> list[dict[str, Any]]: ...
    def insert_task(self, list_id: str, body: dict[str, Any], parent: str | None) -> dict[str, Any]: ...
    def patch_task(self, list_id: str, task_id: str, body: dict[str, Any]) -> dict[str, Any]: ...
    def move_task(self, list_id: str, task_id: str, parent: str | None) -> dict[str, Any]: ...
    def delete_task(self, list_id: str, task_id: str) -> None: ...


GoogleAccountStatus = Literal["unverified", "verified", "different_account", "unowned_links"]
ProviderActivity = Literal["idle", "syncing", "refreshing_calendars"]


class SyncStatus(BaseModel):
    last_attempt_at: str | None
    last_success_at: str | None
    last_error: str | None
    paused_at: str | None = None  # Automatic sync is paused since then (manual Sync now still works).
    syncing: bool = False  # A sync is running right now.
    account_status: GoogleAccountStatus = "unverified"
    account_review_key: str | None = None
    other_account: bool = False  # Signed in to a different Google account; see google_account.py.
    pending_create: dict[str, str] | None = None
    pending_create_unverified: bool = False
    synced_lists: int
    synced_tasks: int
    synced_events: int


@dataclass(frozen=True)
class _Mapping:
    task_id: str
    list_id: str
    google_id: str
    pushed_status: str


# --------------------------------------------------------------------------- reading


def _create_context(db: Database, kind: str, local_id: str) -> str:
    """Display local context only; never use names to infer a remote identity."""
    if kind == "calendar":
        return "BearPlans calendar"
    queries = {
        "task_list": "SELECT name FROM projects WHERE id = ?",
        "task": "SELECT title FROM tasks WHERE id = ?",
        "event": "SELECT t.title FROM planned_items p JOIN tasks t ON t.id = p.task_id WHERE p.id = ?",
    }
    with db.read() as conn:
        row = conn.execute(queries[kind], (local_id,)).fetchone()
    return row[0] if row else "This local item is no longer available"


def get_status(db: Database, verified_key: str | None = None) -> SyncStatus:
    with db.read() as conn:
        row = conn.execute(
            "SELECT (SELECT count(*) FROM google_task_lists) AS lists,"
            " (SELECT count(*) FROM google_tasks) AS tasks,"
            " (SELECT count(*) FROM google_events) AS events, google_sync.*"
            " FROM (SELECT 1 AS id) AS singleton LEFT JOIN google_sync USING (id)"
        ).fetchone()
    owner, candidate = row["account_key"], row["other_account_key"]
    account_status: GoogleAccountStatus = "unverified"
    review_key = None
    if verified_key is not None:
        if verified_key == owner:
            account_status = "verified"
        elif verified_key == candidate:
            account_status = "different_account" if owner else "unowned_links"
            review_key = account_review_key(owner, verified_key)
    pending = pending_for(db, owner) if owner else None
    visible_pending = pending if verified_key == owner else None
    return SyncStatus(
        pending_create_unverified=bool(pending and not visible_pending),
        pending_create={"kind": visible_pending.resource_kind, "review_key": create_review_key(visible_pending),
                        "context": _create_context(db, visible_pending.resource_kind, visible_pending.local_id)} if visible_pending else None,
        last_attempt_at=row["last_attempt_at"], last_success_at=row["last_success_at"],
        last_error=row["last_error"], paused_at=row["paused_at"],
        account_status=account_status, account_review_key=review_key, other_account=review_key is not None,
        synced_lists=row["lists"], synced_tasks=row["tasks"], synced_events=row["events"],
    )


def set_paused(db: Database, paused: bool) -> bool:
    """Return whether the preference changed, preserving the first Pause time."""
    with db.write() as conn:
        conn.execute("INSERT INTO google_sync (id) VALUES (1) ON CONFLICT(id) DO NOTHING")
        if paused:
            return conn.execute(
                "UPDATE google_sync SET paused_at = ? WHERE id = 1 AND paused_at IS NULL", (utc_now(),)
            ).rowcount == 1
        return conn.execute(
            "UPDATE google_sync SET paused_at = NULL WHERE id = 1 AND paused_at IS NOT NULL"
        ).rowcount == 1


def is_paused(db: Database) -> bool:
    return get_status(db).paused_at is not None


def _snapshot(conn: sqlite3.Connection) -> tuple[dict[str, str], list[Task], dict[str, list[str]], dict[str, str], dict[str, _Mapping]]:
    projects = {row["id"]: row["name"] for row in conn.execute("SELECT id, name FROM projects ORDER BY created_at, rowid")}
    tasks = _list_tasks(conn)
    plans: dict[str, list[str]] = {}
    for row in conn.execute("SELECT task_id, planned_date FROM planned_items ORDER BY planned_date"):
        plans.setdefault(row["task_id"], []).append(row["planned_date"])
    lists = {row["project_id"]: row["list_id"] for row in conn.execute("SELECT project_id, list_id FROM google_task_lists")}
    mapped = {row["task_id"]: _Mapping(row["task_id"], row["list_id"], row["google_id"], row["pushed_status"])
              for row in conn.execute("SELECT * FROM google_tasks")}
    return projects, tasks, plans, lists, mapped


def _google_date(task: Task, plans: dict[str, list[str]], children: list[Task], today: str) -> str | None:
    """Deadline, else the next planned day (or latest past one), else none."""
    if task.deadline is not None:
        return task.deadline.isoformat()
    days = list(plans.get(task.id, []))
    for child in children:
        days += plans.get(child.id, [])
    if not days:
        return None
    upcoming = sorted(day for day in days if day >= today)
    return upcoming[0] if upcoming else max(days)


def _desired(task: Task, due: str | None) -> dict[str, Any]:
    return {
        "title": task.title,
        "notes": task.notes[:NOTES_LIMIT],
        "due": f"{due}T00:00:00.000Z" if due else None,
        "status": "completed" if task.completed else "needsAction",
    }


def _differs(remote: dict[str, Any], desired: dict[str, Any]) -> bool:
    return (remote.get("title", "") != desired["title"]
            or (remote.get("notes") or "") != desired["notes"]
            or (remote.get("due") or "")[:10] != (desired["due"] or "")[:10]
            or remote.get("status") != desired["status"])


# --------------------------------------------------------------------------- writing


def _record(db: Database, sql: str, params: tuple[Any, ...]) -> None:
    with db.write() as conn:
        conn.execute(sql, params)


def _save_mapping(db: Database, task_id: str, list_id: str, google_id: str, status: str) -> None:
    _record(db, "INSERT INTO google_tasks (task_id, list_id, google_id, pushed_status, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(task_id) DO UPDATE SET list_id = excluded.list_id, google_id = excluded.google_id, "
                "pushed_status = excluded.pushed_status, updated_at = excluded.updated_at",
            (task_id, list_id, google_id, status, utc_now()))


def _set_sync(db: Database, *, success: bool, error: str | None) -> None:
    now = utc_now()
    with db.write() as conn:
        conn.execute("INSERT INTO google_sync (id) VALUES (1) ON CONFLICT(id) DO NOTHING")
        if success:
            conn.execute("UPDATE google_sync SET last_attempt_at = ?, last_success_at = ?, last_error = NULL WHERE id = 1", (now, now))
        else:
            conn.execute("UPDATE google_sync SET last_attempt_at = ?, last_error = ? WHERE id = 1", (now, error))


def _try_record_sync_error(db: Database, message: str) -> None:
    try:
        _set_sync(db, success=False, error=message)
    except (sqlite3.Error, OSError):
        pass  # A durable intent, if present, remains the source of truth.


def _apply_ticks(db: Database, ticks: dict[str, str]) -> int:
    """Bring completion ticked in Google into BearPlans; returns how many tasks changed.

    Applied only where BearPlans still has the completion it last sent, so a change
    made in BearPlans since then wins. Parent status is derived from subtasks.
    """
    changed = 0
    with db.write() as conn:
        tasks = {task.id: task for task in _list_tasks(conn)}
        mapped = {row["task_id"]: row["pushed_status"] for row in conn.execute("SELECT task_id, pushed_status FROM google_tasks")}
        for task_id, status in ticks.items():
            task = tasks.get(task_id)
            pushed = mapped.get(task_id)
            if task is None or task.is_parent or pushed is None:
                continue
            if ("completed" if task.completed else "needsAction") != pushed:
                continue
            _set_completion_tx(conn, task_id, status == "completed")
            changed += 1
            conn.execute("UPDATE google_tasks SET pushed_status = ?, updated_at = ? WHERE task_id = ?", (status, utc_now(), task_id))
    return changed


# --------------------------------------------------------------------------- sync


def sync(db: Database, client: TasksClient, unavailable: type[Exception],
         calendar: CalendarClient | None = None, remember: Callable[[str], None] | None = None) -> SyncStatus:
    """One full sync (Tasks, BearPlans calendar, then reading followed calendars). Raises `unavailable` (after recording it) when Google fails."""
    failure_context = ""
    owner = None
    try:
        if calendar is None:
            raise unavailable("google_account_unverified", "Verify the Google account before syncing.")
        owner = check_account(db, calendar, unavailable, remember)  # type: ignore[arg-type]
        require_clear(db, owner)
        _sync(db, client, owner)
        if calendar is not None:
            failure_context = "Google Tasks finished, but publishing to the BearPlans calendar did not finish."
            sync_calendar(db, calendar, account_key=owner)
            failure_context = "Google Tasks and calendar publishing finished, but reading selected calendars did not finish."
            read_calendars(db, calendar)  # type: ignore[arg-type]
        _set_sync(db, success=True, error=None)
        return get_status(db)
    except PendingCreate as error:
        message = f"{failure_context} {error}".strip()
        _try_record_sync_error(db, message)
        raise unavailable("google_create_review_required", message) from None
    except unavailable as error:
        message = getattr(error, "message", str(error))
        if owner and pending_for(db, owner):
            message = "Google could not confirm a create. Open Google to review before syncing again."
            if failure_context:
                message = f"{failure_context} {message}"
            _try_record_sync_error(db, message)
            raise unavailable("google_create_review_required", message) from None
        if failure_context:
            message = f"{failure_context} {message}"
        _try_record_sync_error(db, message)
        if failure_context:
            raise unavailable(error.code, message) from None  # type: ignore[attr-defined]
        raise
    except (sqlite3.Error, OSError):
        try:
            uncertain = bool(owner and pending_for(db, owner))
        except (sqlite3.Error, OSError):
            uncertain = True  # Storage is unavailable; do not assume the create failed.
        if uncertain:
            message = "BearPlans could not save Google sync progress. A Google item may already exist; open Google to review before syncing again."
            code = "google_create_review_required"
        else:
            message = "BearPlans could not save Google sync progress. Check storage availability before trying again."
            code = "google_storage_unavailable"
        if failure_context:
            message = f"{failure_context} {message}"
        _try_record_sync_error(db, message)
        raise unavailable(code, message) from None


def _sync(db: Database, client: TasksClient, owner: str) -> None:
    with db.read() as conn:
        _, _, _, lists, mapped = _snapshot(conn)

    # 1. Read what Google has in BearPlans' lists; forget lists the user deleted there.
    present = {item["id"] for item in client.lists() if isinstance(item.get("id"), str)}
    for project_id, list_id in list(lists.items()):
        if list_id not in present:
            _record(db, "DELETE FROM google_tasks WHERE list_id = ?", (list_id,))
            _record(db, "DELETE FROM google_task_lists WHERE project_id = ?", (project_id,))
            del lists[project_id]
    remote: dict[str, dict[str, Any]] = {}
    for list_id in lists.values():
        for item in client.tasks(list_id):
            if isinstance(item.get("id"), str):
                remote[item["id"]] = item

    # 2. Bring back completion ticked in Google.
    ticks = {m.task_id: item["status"] for m in mapped.values()
             if (item := remote.get(m.google_id)) and not item.get("deleted")
             and item.get("status") in ("completed", "needsAction") and item["status"] != m.pushed_status}
    if ticks:
        _apply_ticks(db, ticks)

    # 3. Send BearPlans to Google.
    with db.read() as conn:
        projects, tasks, plans, lists, mapped = _snapshot(conn)
    today = application_today()[0].isoformat()
    children: dict[str, list[Task]] = {}
    for task in tasks:
        if task.parent_id:
            children.setdefault(task.parent_id, []).append(task)
    titles = {item["id"]: item.get("title") for item in client.lists() if isinstance(item.get("id"), str)}

    for project_id, name in projects.items():
        list_id = lists.get(project_id)
        if list_id is None:
            intent = begin(db, owner, "task_list", project_id)
            created_id = returned_id(client.insert_list(name), 200)
            def save_list(conn: sqlite3.Connection) -> None:
                if not conn.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone():
                    raise PendingCreate("The project changed while Google was creating a list. Review the result.")
                conn.execute("INSERT INTO google_task_lists (project_id, list_id, created_at) VALUES (?, ?, ?)",
                             (project_id, created_id, utc_now()))
            publish(db, intent, save_list)
            lists[project_id] = created_id
        elif titles.get(list_id) != name:
            client.rename_list(list_id, name)

    google_ids: dict[str, str] = {}
    local_ids = {task.id for task in tasks}
    for task in tasks:  # parents come before their subtasks
        list_id = lists[task.project_id]
        parent_google = google_ids.get(task.parent_id) if task.parent_id else None
        desired = _desired(task, _google_date(task, plans, children.get(task.id, []), today))
        current = mapped.get(task.id)
        item = remote.get(current.google_id) if current else None
        if current and (item is None or item.get("deleted") or current.list_id != list_id):
            if item is not None and not item.get("deleted"):
                client.delete_task(current.list_id, current.google_id)  # moved to another project
            current, item = None, None
        if current is None:
            intent = begin(db, owner, "task", task.id, list_id)
            created_id = returned_id(client.insert_task(list_id, {k: v for k, v in desired.items() if v is not None}, parent_google), 200)
            def save_task(conn: sqlite3.Connection) -> None:
                row = conn.execute("SELECT project_id, parent_id FROM tasks WHERE id = ?", (task.id,)).fetchone()
                project_list = conn.execute("SELECT list_id FROM google_task_lists WHERE project_id = ?", (task.project_id,)).fetchone()
                if not row or row["project_id"] != task.project_id or row["parent_id"] != task.parent_id or not project_list or project_list["list_id"] != list_id:
                    raise PendingCreate("The task or its project changed while Google was creating it. Review the result.")
                if task.parent_id:
                    parent = conn.execute("SELECT google_id FROM google_tasks WHERE task_id = ? AND list_id = ?", (task.parent_id, list_id)).fetchone()
                    if not parent or parent["google_id"] != parent_google:
                        raise PendingCreate("The parent task changed while Google was creating it. Review the result.")
                conn.execute("INSERT INTO google_tasks (task_id, list_id, google_id, pushed_status, updated_at) VALUES (?, ?, ?, ?, ?) "
                             "ON CONFLICT(task_id) DO UPDATE SET list_id = excluded.list_id, google_id = excluded.google_id, "
                             "pushed_status = excluded.pushed_status, updated_at = excluded.updated_at",
                             (task.id, list_id, created_id, desired["status"], utc_now()))
            publish(db, intent, save_task)
            google_ids[task.id] = created_id
            continue
        google_ids[task.id] = current.google_id
        if (item.get("parent") or None) != parent_google:
            client.move_task(list_id, current.google_id, parent_google)
        if _differs(item, desired):
            body = dict(desired)
            if desired["status"] == "needsAction":
                body["completed"] = None
            client.patch_task(list_id, current.google_id, body)
        if current.pushed_status != desired["status"]:
            _save_mapping(db, task.id, list_id, current.google_id, desired["status"])

    # 4. Remove from Google what was removed in BearPlans (subtasks first).
    gone = [m for m in mapped.values() if m.task_id not in local_ids]
    gone.sort(key=lambda m: 0 if (remote.get(m.google_id) or {}).get("parent") else 1)
    for mapping in gone:
        client.delete_task(mapping.list_id, mapping.google_id)
        _record(db, "DELETE FROM google_tasks WHERE task_id = ?", (mapping.task_id,))


# --------------------------------------------------------------------------- background


class GoogleSyncService:
    """Runs sync in the background: every PERIOD_SECONDS, and shortly after a change."""

    def __init__(self, db: Database, client_factory: Any, unavailable: type[Exception], connected: Any,
                 calendar_factory: Any = None, remember: Callable[[str], None] | None = None) -> None:
        self._db = db
        self._client_factory = client_factory
        self._calendar_factory = calendar_factory
        self._remember_account = remember
        self._unavailable = unavailable
        self._connected = connected
        self._lock = threading.Lock()
        self._preference_lock = threading.Lock()
        self._manual_sync_lock = threading.Lock()
        self.pausing = False
        self.activity: ProviderActivity = "idle"
        self.connection_lock = threading.Lock()
        # None blocks new provider work. A fresh object invalidates old queued work
        # even if the credential was replaced and the user is already signed in again.
        self._connection_epoch: object | None = object()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._version = 0

    @property
    def version(self) -> int:
        """Goes up whenever a sync changes something the open page shows (a tick from
        Google, followed-calendar events), so the page knows to refresh."""
        return self._version

    def _fingerprint(self) -> int:
        with self._db.read() as conn:
            return hash((
                tuple(tuple(row) for row in conn.execute("SELECT id, revision, completed_at FROM tasks ORDER BY id")),
                tuple(tuple(row) for row in conn.execute("SELECT * FROM google_source_events ORDER BY calendar_id, event_id")),
                tuple(tuple(row) for row in conn.execute("SELECT calendar_id, summary, followed, in_source FROM google_source_calendars ORDER BY calendar_id")),
            ))

    def sync_once(self) -> None:
        """Run one deliberate sync and reject overlapping requests."""
        if not self._manual_sync_lock.acquire(blocking=False):
            raise self._unavailable("google_sync_busy", "A requested Google sync is already in progress.")
        try:
            self.sync_now()
        finally:
            self._manual_sync_lock.release()

    def sync_now(self, automatic: bool = False) -> SyncStatus | None:
        """One sync. An automatic one is skipped (None) while sync is paused; the
        check happens under the lock, so a Pause that returned stops later automatic work."""
        epoch = self._connection_epoch
        with self._lock:  # one provider operation at a time
            if not self._current_connection(epoch):
                if automatic:
                    return None
                raise self._connection_changed()
            if not self._connected():
                if automatic:
                    return None
                raise self._unavailable("google_not_connected", "Google is not connected. Choose Connect Google first.")
            if automatic and (self.pausing or is_paused(self._db)):
                return None
            with self._active("syncing"):
                calendar = self._calendar_factory() if self._calendar_factory else None
                before = self._fingerprint()
                try:
                    return sync(self._db, self._client_factory(), self._unavailable, calendar, self._remember_account)
                finally:
                    if self._fingerprint() != before:
                        self._version += 1

    @property
    def syncing(self) -> bool:
        return self.activity == "syncing"

    @property
    def connection_changing(self) -> bool:
        return self._connection_epoch is None

    @contextmanager
    def _active(self, activity: ProviderActivity) -> Iterator[None]:
        # Only set under the provider operation lock.
        self.activity = activity
        try:
            yield
        finally:
            self.activity = "idle"

    @contextmanager
    def changing_connection(self) -> Iterator[None]:
        """Exclude new provider work and other connection changes during teardown."""
        with self.connection_lock:
            self._connection_epoch = None
            try:
                yield
            finally:
                self._connection_epoch = object()

    def _current_connection(self, epoch: object | None) -> bool:
        return epoch is not None and self._connection_epoch is epoch

    def _connection_changed(self) -> Exception:
        return self._unavailable(
            "google_connection_changed", "The Google connection is being updated or changed. Check Settings and try again."
        )

    def publish_authorization(self, publish: Callable[[], bool]) -> None:
        with self.changing_connection():
            if self.while_idle(publish):
                self._version += 1

    def read_from_google(self, action: Callable[[], _Result], *, automatic: bool = False) -> _Result | None:
        epoch = self._connection_epoch

        def read() -> _Result | None:
            if not self._current_connection(epoch):
                raise self._connection_changed()
            if automatic and (self.pausing or is_paused(self._db)):
                return None
            with self._active("refreshing_calendars"):
                return action()

        return self.while_idle(read)

    def change_pause(self, paused: bool, snapshot: Callable[[], _Result]) -> _Result:
        """Acknowledge a preference change at the provider operation boundary."""
        if not self._preference_lock.acquire(blocking=False):
            raise self._unavailable(
                "google_preference_busy", "Google sync settings are already changing. Wait for that change, then try again."
            )
        self.pausing = paused
        try:
            def apply() -> tuple[_Result, bool]:
                changed = set_paused(self._db, paused)
                self.pausing = False
                return snapshot(), changed

            result, changed = self.while_idle(apply)
            if changed and not paused:
                self.nudge()
            return result
        finally:
            self.pausing = False
            self._preference_lock.release()

    def while_idle(self, action: Callable[[], _Result], wait_seconds: float = 30.0) -> _Result:
        """Run action after active Google work, or fail without running it."""
        if not self._lock.acquire(timeout=wait_seconds):
            raise self._unavailable(
                "google_sync_busy", "Google sync or a calendar refresh is still running. Wait for it to finish, then try again."
            )
        try:
            return action()
        finally:
            self._lock.release()

    def nudge(self) -> None:
        self._wake.set()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()

        def run() -> None:
            while not self._stop.is_set():
                woken = self._wake.wait(PERIOD_SECONDS)
                if self._stop.is_set():
                    break
                if woken:
                    self._stop.wait(NUDGE_DELAY_SECONDS)  # gather a burst of edits
                    self._wake.clear()
                if not self._connected():
                    continue
                try:
                    self.sync_now(automatic=True)
                except self._unavailable:
                    pass  # recorded in google_sync and shown in the app
                except (sqlite3.Error, OSError):
                    _LOG.warning("Google Tasks sync could not save its progress; it will retry.")

        self._thread = threading.Thread(target=run, daemon=True, name="bearplans-google-sync")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

