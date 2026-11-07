"""Pause / Resume automatic Google sync, safer Disconnect (cancel, wait, revoke) and the status summary."""

from __future__ import annotations

import json
import socket
import stat
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.domain.google_tasks import GoogleSyncService, is_paused, set_paused
from backend.domain.google_reading import list_events, read_calendars, refresh_events, set_followed
from backend.domain.planning import create_placement, move_placement, set_placement_time
from backend.domain.tasks import create_task, get_task, set_task_completion, update_task
from backend.platform import google
from backend.platform.google import SCOPES, GoogleAuth, GoogleUnavailable, client_file, revoke_token, token_file
from backend.storage.db import Database, open_database
from backend.storage.migrations import MigrationError, current_version, load_migrations, migrate
from tests.test_google_calendar import FakeCalendar
from tests.test_google_reading import D1, D3, FakeReader
from tests.test_google_tasks import FakeTasks

CLIENT = {"installed": {"client_id": "1-a.apps.googleusercontent.com", "client_secret": "s",
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}}


def _signed_in(scope="https://www.googleapis.com/auth/tasks https://www.googleapis.com/auth/calendar.app.created "
                     "https://www.googleapis.com/auth/calendar.calendarlist.readonly https://www.googleapis.com/auth/calendar.events.readonly"):
    client_file().parent.mkdir(parents=True, exist_ok=True)
    client_file().write_text(json.dumps(CLIENT))
    token_file().write_text(json.dumps({"refresh_token": "refresh-1", "scope": scope}))


def _app(db, fake=None):
    reader = FakeReader()
    app = create_app(db, google_tasks_client=fake or FakeTasks(), google_calendar_client=reader)
    app.state.google_calendar_factory = lambda: reader if app.state.google_auth.connected() else None
    return TestClient(app, base_url="http://127.0.0.1:8765")


def test_pause_survives_restart_and_stops_only_automatic_sync(db):
    fake = FakeTasks()
    create_task(db, "Essay")
    with _app(db, fake) as client:
        state = client.post("/api/google/pause").json()
        assert state["tasks"]["paused_at"] and state["status"] == "not_set_up"  # No sign-in file in this test.
        first = state["tasks"]["paused_at"]
        assert client.post("/api/google/pause").json()["tasks"]["paused_at"] == first  # Pausing again keeps the time.
    reopened = open_database(db.path)
    service = GoogleSyncService(reopened, lambda: fake, GoogleUnavailable, lambda: True, FakeReader)
    assert is_paused(reopened)
    assert service.sync_now(automatic=True) is None and fake.calls == []
    with _app(reopened, fake) as client:
        assert client.get("/api/google").json()["tasks"]["paused_at"] == first
        assert client.post("/api/google/tasks/sync").status_code == 200  # Sync now still runs once ...
        assert fake.calls and client.get("/api/google").json()["tasks"]["paused_at"] == first  # ... and stays paused.
        assert client.post("/api/google/resume").json()["tasks"]["paused_at"] is None
    resumed = open_database(db.path)
    assert not is_paused(resumed)
    assert GoogleSyncService(resumed, lambda: fake, GoogleUnavailable, lambda: True, FakeReader).sync_now(automatic=True) is not None


@pytest.mark.parametrize("version", [19, 20])
def test_pause_upgrade_preserves_saved_work_and_sync_evidence(tmp_path, version):
    path = tmp_path / "pause-upgrade.sqlite3"
    old = Database(path)
    migrations = load_migrations()
    assert migrate(old, migrations[:version]) == version
    task = create_task(old, "Essay")
    instant = "2026-11-05T12:00:00.000000Z"
    with old.write() as conn:
        conn.execute(
            "INSERT INTO google_sync (id, last_attempt_at, last_success_at, last_error) "
            "VALUES (1, ?, ?, 'Previously offline')", (instant, instant),
        )
        conn.execute(
            "INSERT INTO google_tasks VALUES (?, 'list', 'remote-task', 'needsAction', ?)",
            (task.id, instant),
        )
        conn.execute(
            "INSERT INTO google_source_calendars (calendar_id, summary, followed, fetched_at) "
            "VALUES ('calendar', 'Seminars', 1, ?)", (instant,),
        )
    expected_pause = None
    if version == 20:
        set_paused(old, True)
        with old.read() as conn:
            expected_pause = conn.execute("SELECT paused_at FROM google_sync").fetchone()[0]
        assert expected_pause is not None
    else:
        pause_migration = migrations[19]
        broken = replace(pause_migration, sql=pause_migration.sql + "\nSELECT * FROM missing_fault_table;")
        with pytest.raises(MigrationError, match="rolled back"):
            migrate(old, [*migrations[:19], broken])
        assert current_version(old) == 19
        with old.read() as conn:
            assert "paused_at" not in {row["name"] for row in conn.execute("PRAGMA table_info(google_sync)")}

    for _ in range(2):
        upgraded = open_database(path)
        assert current_version(upgraded) == len(migrations)
        assert get_task(upgraded, task.id) == task
        with upgraded.read() as conn:
            row = conn.execute(
                "SELECT paused_at, last_attempt_at, last_success_at, last_error FROM google_sync"
            ).fetchone()
            assert tuple(row) == (expected_pause, instant, instant, "Previously offline")
            assert tuple(conn.execute("SELECT * FROM google_tasks").fetchone()) == (
                task.id, "list", "remote-task", "needsAction", instant,
            )
            assert tuple(conn.execute(
                "SELECT calendar_id, summary, followed, fetched_at FROM google_source_calendars"
            ).fetchone()) == ("calendar", "Seminars", 1, instant)
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize(("was_paused", "action"), [(False, "pause"), (True, "resume")])
def test_failed_preference_write_preserves_saved_state(db, was_paused, action):
    set_paused(db, was_paused)
    with db.write() as conn:
        conn.execute("CREATE TRIGGER fail_preference BEFORE UPDATE OF paused_at ON google_sync "
                     "BEGIN SELECT RAISE(ABORT, 'Injected preference write failure'); END")
    with _app(db) as client:
        before = client.get("/api/google").json()["tasks"]["paused_at"]
        assert (before is not None) == was_paused
        failed = client.post(f"/api/google/{action}")
        assert failed.status_code == 503 and failed.json()["error"]["code"] == "storage_unavailable"
    reopened = open_database(db.path)
    with reopened.write() as conn:
        conn.execute("DROP TRIGGER fail_preference")
    with _app(reopened) as client:
        assert client.get("/api/google").json()["tasks"]["paused_at"] == before
        retried = client.post(f"/api/google/{action}").raise_for_status().json()["tasks"]["paused_at"]
        assert (retried is not None) != was_paused
    assert is_paused(open_database(db.path)) != was_paused


@pytest.mark.parametrize("trigger", ["periodic", "local_edit"])
def test_background_worker_does_nothing_while_paused(db, monkeypatch, trigger):
    from backend.domain import google_tasks

    monkeypatch.setattr(google_tasks, "PERIOD_SECONDS", 0.01 if trigger == "periodic" else 60)
    monkeypatch.setattr(google_tasks, "NUDGE_DELAY_SECONDS", 0)
    set_paused(db, True)
    reopened = open_database(db.path)
    fake = FakeTasks()
    attempted = threading.Event()
    client = _app(reopened, fake)
    service = client.app.state.google_sync
    original_sync = service.sync_now

    def observed_sync(automatic=False):
        result = original_sync(automatic=automatic)
        attempted.set()
        return result

    monkeypatch.setattr(service, "sync_now", observed_sync)
    with client:
        if trigger == "local_edit":
            saved = client.post("/api/tasks", json={"title": "Essay"}).raise_for_status().json()
            assert get_task(reopened, saved["id"]).title == "Essay"
        assert attempted.wait(3)
        assert fake.calls == []
        assert client.get("/api/google").json()["tasks"]["last_attempt_at"] is None


def test_automatic_calendar_refresh_rechecks_pause_after_waiting(db, monkeypatch):
    reads = []

    class Calendar(FakeReader):
        def calendar_list(self):
            reads.append("calendar list")
            return super().calendar_list()

    app = create_app(db, google_calendar_client=Calendar())
    client = TestClient(app, base_url="http://127.0.0.1:8765")
    service = app.state.google_sync
    while_idle = service.while_idle
    queued = threading.Event()

    def observe_queue(action):
        queued.set()
        return while_idle(action)

    monkeypatch.setattr(service, "while_idle", observe_queue)
    endpoint = "/api/google/calendars/refresh"
    with ThreadPoolExecutor(max_workers=1) as pool:
        def queue_then_pause():
            assert client.get("/api/google/calendars").json() == []
            future = pool.submit(client.post, endpoint, params={"automatic": "true"})
            assert queued.wait(3)
            set_paused(db, True)
            return future

        stale = while_idle(queue_then_pause)
        assert stale.result(3).raise_for_status().json() == []

    assert reads == []
    assert client.get("/api/google/calendars").json() == []
    assert client.post(endpoint).raise_for_status().json()
    assert reads
    assert is_paused(db)


@pytest.mark.parametrize("stage", ["tasks", "publish", "read"])
def test_pause_waits_for_a_running_sync(db, monkeypatch, stage):
    from backend.domain import google_tasks

    release, started, pausing = threading.Event(), threading.Event(), threading.Event()
    stages = []

    def visit(name):
        stages.append(name)
        if stage == name:
            started.set()
            assert release.wait(5)

    class Slow(FakeTasks):
        def lists(self):
            if "tasks" not in stages:
                visit("tasks")
            return super().lists()

    fake = Slow()
    monkeypatch.setattr(google_tasks, "sync_calendar", lambda *_, **__: visit("publish"))
    monkeypatch.setattr(google_tasks, "read_calendars", lambda *_: visit("read"))
    app = create_app(db, google_tasks_client=fake, google_calendar_client=FakeReader())
    client = TestClient(app, base_url="http://127.0.0.1:8765")
    service = app.state.google_sync
    while_idle = service.while_idle

    def watch_wait(action):
        if service.pausing:
            pausing.set()
        return while_idle(action)

    monkeypatch.setattr(service, "while_idle", watch_wait)
    with ThreadPoolExecutor(max_workers=3) as pool:
        running = pool.submit(service.sync_now, automatic=True)
        try:
            assert started.wait(3)
            pause = pool.submit(client.post, "/api/google/pause")
            assert pausing.wait(3)
            snapshot = client.get("/api/google").json()
            assert snapshot["pausing"] and snapshot["status"] == "pausing"
            assert snapshot["activity"] == "syncing" and snapshot["tasks"]["paused_at"] is None
            assert not pause.done()
            for action in ("pause", "resume"):
                busy = client.post(f"/api/google/{action}")
                assert busy.json()["error"]["code"] == "google_preference_busy"
                assert busy.is_error
            queued = pool.submit(service.sync_now, automatic=True)
        finally:
            release.set()
        assert running.result(3) is not None
        state = pause.result(3).raise_for_status().json()
        assert not state["pausing"] and state["activity"] == "idle" and state["tasks"]["paused_at"]
        assert queued.result(3) is None
    assert stages == ["tasks", "publish", "read"]
    assert client.post("/api/google/resume").raise_for_status().json()["tasks"]["paused_at"] is None


def test_pause_timeout_preserves_preference_and_allows_retry(db, monkeypatch):
    client = _app(db)
    service = client.app.state.google_sync
    while_idle = service.while_idle
    monkeypatch.setattr(service, "while_idle", lambda action: while_idle(action, wait_seconds=0))

    response = while_idle(lambda: client.post("/api/google/pause"))
    assert response.is_error and response.json()["error"]["code"] == "google_sync_busy"
    assert not is_paused(db)
    assert client.get("/api/google").json()["pausing"] is False
    assert client.post("/api/google/pause").raise_for_status().json()["tasks"]["paused_at"]


def test_status_separates_setup_saved_grant_and_permissions(db):
    with _app(db) as client:
        def read_status():
            return client.get("/api/google").json()

        assert read_status()["setup"] == "missing"
        client_file().parent.mkdir(parents=True, exist_ok=True)
        client_file().write_text(json.dumps({"installed": {**CLIENT["installed"], "client_secret": " "}}))
        assert read_status()["setup"] == "unusable"
        assert client.get("/api/connections").json()["google"]["setup"] == "unusable"
        client_file().write_text(json.dumps(CLIENT))
        state = read_status()
        assert state["setup"] == "configured" and state["status"] == "signed_out"
        assert not state["connected"] and state["tasks"]["last_success_at"] is None
        _signed_in(scope="https://www.googleapis.com/auth/tasks")
        state = read_status()
        assert state["connected"] and state["status"] == "needs_attention"
        assert set(state["missing_permissions"]) == {
            "calendar.app.created", "calendar.calendarlist.readonly", "calendar.events.readonly",
        }
        _signed_in()
        state = read_status()
        assert state["connected"] and state["status"] == "not_synced"
        assert state["tasks"]["account_status"] == "unverified"
        assert client.post("/api/google/pause").json()["status"] == "paused"


def test_overlapping_sync_once_is_rejected_and_pause_stays_saved(db):
    started, release = threading.Event(), threading.Event()
    passes = []

    class SlowTasks(FakeTasks):
        def lists(self):
            passes.append("list")
            started.set()
            assert release.wait(5)
            return super().lists()

    fake = SlowTasks()
    create_task(db, "Essay")
    client = _app(db, fake)
    paused_at = client.post("/api/google/pause").raise_for_status().json()["tasks"]["paused_at"]
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(client.post, "/api/google/tasks/sync")
        try:
            assert started.wait(3)
            duplicate = client.post("/api/google/tasks/sync")
            assert duplicate.is_error and duplicate.json()["error"]["code"] == "google_sync_busy"
        finally:
            release.set()
        assert first.result(3).raise_for_status().json()["tasks"]["paused_at"] == paused_at
    assert passes == ["list", "list"]  # One full sync reads list IDs and titles.
    assert fake.calls.count("insert_task") == 1
    assert client.app.state.google_sync.sync_now(automatic=True) is None
    assert is_paused(open_database(db.path))


def test_resume_reconciles_latest_task_and_calendar_state_once(db, monkeypatch):
    class Calendar(FakeCalendar):
        def calendar_list(self):
            return [{"id": "primary", "primary": True, "summary": "Personal"}]

        def list_events(self, calendar_id, time_min, time_max):
            return []

    fake, calendar = FakeTasks(), Calendar()
    app = create_app(db, google_tasks_client=fake, google_calendar_client=calendar)
    client = TestClient(app, base_url="http://127.0.0.1:8765")
    service = app.state.google_sync
    wakes = []
    monkeypatch.setattr(service, "nudge", lambda: wakes.append("reconcile"))
    draft = create_task(db, "First draft")
    complete = create_task(db, "Finish locally")
    placement = create_placement(db, draft.id, D1)
    set_placement_time(db, placement.id, "12:00")
    client.post("/api/google/tasks/sync").raise_for_status()
    [original_event] = calendar.live()
    list_id = fake.list_named("Inbox")
    original_task_id = fake.live(list_id)["First draft"]["id"]
    client.post("/api/google/pause").raise_for_status()

    update_task(db, draft.id, title="Intermediate draft")
    move_placement(db, placement.id, D3)
    set_placement_time(db, placement.id, "15:00")
    update_task(db, draft.id, title="Final draft")
    set_task_completion(db, complete.id, True)
    assert service.sync_now(automatic=True) is None
    assert fake.live(list_id)["First draft"]["id"] == original_task_id
    assert calendar.live()[0]["start"] == original_event["start"]

    for _ in range(2):
        assert client.post("/api/google/resume").raise_for_status().json()["tasks"]["paused_at"] is None
    assert wakes == ["reconcile"]
    assert service.sync_now(automatic=True) is not None
    [event] = calendar.live()
    assert event["id"] == original_event["id"] and event["summary"] == "Final draft"
    assert event["start"]["dateTime"].startswith(f"{D3}T15:00:00")
    remote = fake.live(list_id)
    assert set(remote) == {"Final draft", "Finish locally"}
    assert remote["Final draft"]["id"] == original_task_id
    assert remote["Finish locally"]["status"] == "completed"
    writes = (fake.calls.copy(), calendar.calls.copy())
    assert service.sync_now(automatic=True) is not None
    assert (fake.calls, calendar.calls) == writes


def test_paused_with_saved_grant_and_failed_sync_keeps_previous_success(db):
    _signed_in()

    class Tasks(FakeTasks):
        expired = False

        def lists(self):
            if self.expired:
                raise GoogleUnavailable("google_signin_expired", "Google sign-in expired. Connect Google again.")
            return super().lists()

    tasks = Tasks()
    with _app(db, tasks) as client:
        client.post("/api/google/pause").raise_for_status()
        first = client.post("/api/google/tasks/sync").json()["tasks"]
        assert first["last_success_at"] and first["paused_at"]
        tasks.expired = True
        failed = client.post("/api/google/tasks/sync")
        assert failed.status_code == 502 and failed.json()["error"]["code"] == "google_signin_expired"
        state = client.get("/api/google").json()
        assert state["connected"] and state["status"] == "needs_attention"
        assert state["activity"] == "idle"
        assert state["tasks"]["last_success_at"] == first["last_success_at"]
        assert state["tasks"]["last_attempt_at"] > first["last_attempt_at"]
        assert state["tasks"]["paused_at"] == first["paused_at"]
        assert "Connect Google again" in state["tasks"]["last_error"]
        assert "refresh-1" not in client.get("/api/google").text


def test_disconnect_deletes_locally_then_revokes(db, revoked_tokens):
    _signed_in()
    with _app(db) as client:
        for headers, status in (({"Origin": "https://evil.example"}, 403), ({"Host": "evil.example"}, 400)):
            assert client.post("/api/google/disconnect", headers=headers).status_code == status
        assert token_file().exists() and revoked_tokens == []
        state = client.post("/api/google/disconnect").json()
        assert state["revoked"] is True and state["connected"] is False and not token_file().exists()
        assert state["connection_changing"] is False
        assert client.get("/api/google").json()["revoked"] is None
        assert revoked_tokens == ["refresh-1"]
        assert client.post("/api/google/disconnect").json()["revoked"] is None  # Nothing left to revoke.
        assert "refresh-1" not in client.get("/api/google").text


def test_disconnect_reports_when_google_could_not_be_asked(db, monkeypatch):
    from backend.platform import google

    monkeypatch.setattr(google, "revoke_token", lambda token: False)
    _signed_in()
    with _app(db) as client:
        state = client.post("/api/google/disconnect").json()
        assert state["revoked"] is False and not token_file().exists()  # Still signed out here.


def test_removing_the_sign_in_file_revokes_too(client, revoked_tokens):
    _signed_in()
    assert client.delete("/api/connections/google").json()["google"]["connected"] is False
    assert revoked_tokens == ["refresh-1"]


@pytest.mark.parametrize("active", ["sync", "calendar"])
def test_disconnect_drains_active_work_and_rejects_old_queued_reads(db, monkeypatch, revoked_tokens, active):
    from backend import app as app_module

    _signed_in()
    active_started, release, queued, closing = (threading.Event() for _ in range(4))
    provider_calls = []

    def block_provider():
        provider_calls.append("active")
        active_started.set()
        assert release.wait(5)

    class SlowTasks(FakeTasks):
        def lists(self):
            if not active_started.is_set():
                block_provider()
            return super().lists()

    class SlowCalendar(FakeReader):
        def calendar_list(self):
            if not active_started.is_set():
                block_provider()
            return super().calendar_list()

    fake = SlowTasks()
    monkeypatch.setattr(app_module, "GoogleTasksClient", lambda auth: fake)
    monkeypatch.setattr(app_module, "GoogleCalendarClient", lambda auth: SlowCalendar())
    app = create_app(db)
    client = TestClient(app, base_url="http://127.0.0.1:8765")
    operation = "/api/google/tasks/sync" if active == "sync" else "/api/google/calendars/refresh"
    service = app.state.google_sync
    original_idle = service.while_idle
    original_change = service.changing_connection

    def watch_read(action, wait_seconds=30):
        if action.__name__ == "read" and active_started.is_set():
            queued.set()
        return original_idle(action, wait_seconds)

    @contextmanager
    def watch_change():
        with original_change():
            closing.set()
            yield

    monkeypatch.setattr(service, "while_idle", watch_read)
    monkeypatch.setattr(service, "changing_connection", watch_change)
    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(client.post, operation)
        try:
            assert active_started.wait(3)
            old = pool.submit(client.post, "/api/google/calendars/refresh")
            assert queued.wait(3)
            disconnect = pool.submit(client.post, "/api/google/disconnect")
            assert closing.wait(3)
            status = client.get("/api/google").json()
            assert status["connection_changing"] is True
            assert status["activity"] == ("syncing" if active == "sync" else "refreshing_calendars")
            assert status["tasks"]["syncing"] is (active == "sync")
            assert not disconnect.done() and token_file().exists() and revoked_tokens == []
        finally:
            release.set()
        assert first.result(4).status_code == 200
        stale = old.result(4)
        assert stale.status_code == 502 and stale.json()["error"]["code"] == "google_connection_changed"
        state = disconnect.result(4).json()
    assert provider_calls == ["active"]
    assert not state["connected"] and state["revoked"] is True
    assert revoked_tokens == ["refresh-1"]
    assert service.sync_now(automatic=True) is None
    assert client.post("/api/google/tasks/sync").json()["error"]["code"] == "google_not_connected"


@pytest.mark.parametrize("automatic", [True, False])
def test_sync_queued_under_old_connection_cannot_use_a_new_one(db, monkeypatch, automatic):
    queued, release = threading.Event(), threading.Event()
    fake = FakeTasks()
    create_task(db, "Essay")
    service = GoogleSyncService(db, lambda: fake, GoogleUnavailable, lambda: True, FakeReader)
    lock = service._lock

    class DelayedSyncLock:
        def __enter__(self):
            queued.set()
            assert release.wait(5)
            return lock.__enter__()

        def __exit__(self, *exc):
            return lock.__exit__(*exc)

    monkeypatch.setattr(service, "_lock", DelayedSyncLock())
    with ThreadPoolExecutor(max_workers=1) as pool:
        old = pool.submit(service.sync_now, automatic)
        try:
            assert queued.wait(3)
            with service.changing_connection():
                pass  # The old call already captured the earlier connection.
        finally:
            release.set()
        if automatic:
            assert old.result(4) is None
        else:
            with pytest.raises(GoogleUnavailable) as stale:
                old.result(4)
            assert stale.value.code == "google_connection_changed"
    assert fake.calls == []
    service.sync_now()
    assert fake.calls


@pytest.mark.parametrize("remove_setup", [False, True])
def test_sign_in_cannot_start_during_revocation(db, monkeypatch, remove_setup):
    _signed_in()
    revoking, release = threading.Event(), threading.Event()
    fake = FakeReader()
    read_calendars(db, fake)
    set_followed(db, ["me@example.com"])
    refresh_events(db, fake)
    cached = list_events(db, D1, D1)
    task = create_task(db, "Keep my local task")

    def revoke(refresh):
        assert refresh == "refresh-1" and not token_file().exists()
        revoking.set()
        assert release.wait(5)
        return False

    monkeypatch.setattr(google, "revoke_token", revoke)
    with _app(db) as client, ThreadPoolExecutor(max_workers=2) as pool:
        paused_at = client.post("/api/google/pause").json()["tasks"]["paused_at"]
        method, path = ("DELETE", "/api/connections/google") if remove_setup else ("POST", "/api/google/disconnect")
        close = pool.submit(client.request, method, path)
        try:
            assert revoking.wait(3)
            reconnect = pool.submit(client.post, "/api/google/connect")
            with pytest.raises(FutureTimeout):
                reconnect.result(timeout=0.1)
            stale_follow = client.put("/api/google/calendars", json={"account_key": "0" * 32, "calendar_ids": []})
            assert stale_follow.json()["error"]["code"] == "google_connection_changed"
            assert client.post("/api/google/tasks/sync").json()["error"]["code"] == "google_connection_changed"
        finally:
            release.set()
        response = close.result(4).json()
        assert (response["google"] if remove_setup else response)["revoked"] is False
        connected = reconnect.result(4)
        if remove_setup:
            assert connected.json()["error"]["code"] == "google_not_configured"
        else:
            attempt = connected.json()["attempt_id"]
            assert client.post("/api/google/cancel-sign-in", json={"attempt_id": attempt}).json()["cancelled"]
        assert not client.get("/api/google").json()["connected"]
        assert client.put("/api/google/calendars", json={"account_key": "0" * 32, "calendar_ids": []}).json()["error"]["code"] == "google_not_connected"
        assert client.get("/api/google").json()["tasks"]["paused_at"] == paused_at
    assert list_events(db, D1, D1) == cached and get_task(db, task.id) == task
    assert client_file().exists() is not remove_setup and not GoogleAuth().connected()


@pytest.mark.parametrize("failure", ["busy", "token", "receipt", "setup"])
def test_remove_google_recovery_is_explicit(db, monkeypatch, revoked_tokens, failure):
    _signed_in()
    with _app(db) as client:
        state = client.app.state
        service = state.google_sync
        idle = service.while_idle
        remove = google.remove_private_file

        def fail_remove(path):
            if path == (token_file() if failure == "token" else client_file()):
                raise PermissionError("private-path-canary")
            return remove(path)

        def fail_receipt(*args):
            raise PermissionError("private-path-canary")

        with monkeypatch.context() as fault:
            if failure == "busy":
                fault.setattr(service, "while_idle", lambda action: idle(action, wait_seconds=0))
                service._lock.acquire()
            elif failure == "token":
                fault.setattr(google, "remove_private_file", fail_remove)
            elif failure == "receipt":
                fault.setattr("backend.routes.connections.update_status", fail_receipt)
            else:
                fault.setattr("backend.routes.connections.remove_private_file", fail_remove)
            try:
                failed = client.delete("/api/connections/google")
            finally:
                if failure == "busy":
                    service._lock.release()
        assert failed.status_code == (502 if failure == "busy" else 503)
        assert "private-path-canary" not in failed.text and "refresh-1" not in failed.text
        assert client_file().exists()
        already_signed_out = failure in {"receipt", "setup"}
        assert token_file().exists() is not already_signed_out
        assert revoked_tokens == (["refresh-1"] if already_signed_out else [])
        result = client.delete("/api/connections/google").json()["google"]
        assert not result["set"] and not result["connected"]
        assert result["revoked"] is (None if already_signed_out else True)
        assert revoked_tokens == ["refresh-1"]


@pytest.mark.parametrize(("status", "confirmed"), [(200, True), (204, False), (400, False), (503, False)])
def test_revocation_acknowledgement_requires_google_success(monkeypatch, status, confirmed):
    @contextmanager
    def open_request(request, *, timeout):
        assert request.full_url == google.REVOKE_URL and request.method == "POST"
        assert timeout == google.TIMEOUT_SECONDS
        if status >= 400:
            raise HTTPError(google.REVOKE_URL, status, "Synthetic Google response", {}, None)
        yield SimpleNamespace(status=status)

    monkeypatch.setattr(google._OPENER, "open", open_request)
    assert revoke_token("fake-refresh") is confirmed


def _callback(url, **params):
    query = parse_qs(urlsplit(url).query)
    callback = query["redirect_uri"][0]
    args = {"state": query["state"][0], **params}
    with urlopen(f"{callback}/?{urlencode(args)}", timeout=3) as reply:
        return reply.read()


def _tokens(refresh="fresh-token", **overrides):
    return {"refresh_token": refresh, "access_token": "fresh-access", "expires_in": 3600,
            "scope": " ".join(SCOPES), **overrides}


def _settled(client):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        state = client.get("/api/google").json()
        if not state["sign_in_pending"]:
            return state
        time.sleep(0.02)
    pytest.fail("Google sign-in did not settle")


@pytest.mark.parametrize("action", ["disconnect", "remove", "replace", "cancel", "retry", "retry-error", "timeout"])
def test_a_sign_in_finishing_after_invalidation_is_dropped(db, monkeypatch, revoked_tokens, action):
    """Even a full grant from an obsolete exchange cannot become the current sign-in."""
    _signed_in()
    exchange_started, finish_exchange = threading.Event(), threading.Event()
    workers = []
    now = [100.0]
    monkeypatch.setattr(google, "time", SimpleNamespace(monotonic=lambda: now[0]))

    def exchange(url, fields):
        if fields.get("code") == "late":
            workers.append(threading.current_thread())
            exchange_started.set()
            assert finish_exchange.wait(5)
            if action == "retry-error":
                raise GoogleUnavailable("google_unreachable", "The older exchange failed.")
            return _tokens("late-token")
        return _tokens()

    monkeypatch.setattr(google, "_post_form", exchange)
    with _app(db) as client:
        original = token_file().read_bytes()
        link = client.post("/api/google/connect").json()
        cancel = {"attempt_id": link["attempt_id"]}
        try:
            _callback(link["url"], code="late")
            assert exchange_started.wait(3)
            if action in {"disconnect", "remove"}:
                path = "/api/google/disconnect" if action == "disconnect" else "/api/connections/google"
                method = "POST" if action == "disconnect" else "DELETE"
                assert client.request(method, path).status_code == 200
            elif action == "replace":
                new = {"installed": {**CLIENT["installed"], "client_id": "2-b.apps.googleusercontent.com"}}
                assert client.put("/api/connections/google", json={"client_file": json.dumps(new)}).status_code == 200
            elif action == "cancel":
                assert client.post("/api/google/cancel-sign-in", json=cancel).json() == {"cancelled": True}
                assert client.post("/api/google/cancel-sign-in", json=cancel).json() == {"cancelled": False}
            elif action in {"retry", "retry-error"}:
                second = client.post("/api/google/connect").json()
                assert client.post("/api/google/cancel-sign-in", json=cancel).json() == {"cancelled": False}
                assert client.get("/api/google").json()["sign_in_attempt_id"] == second["attempt_id"]
                _callback(second["url"], code="new")
                assert _settled(client)["sign_in_error"] is None
                assert client.post("/api/google/cancel-sign-in", json={"attempt_id": second["attempt_id"]}).json() == {"cancelled": False}
            else:
                now[0] += google.SIGN_IN_WAIT_SECONDS - 0.001
                assert client.get("/api/google").json()["sign_in_pending"]
                now[0] += 0.001
                assert client.post("/api/google/cancel-sign-in", json=cancel).json() == {"cancelled": False}
                assert "in time" in _settled(client)["sign_in_error"]
        finally:
            finish_exchange.set()
            for worker in workers:
                worker.join(5)
                assert not worker.is_alive()

        state = _settled(client)
        assert state["sign_in_attempt_id"] is None
        if action in {"disconnect", "remove", "replace"}:
            assert not state["connected"] and not token_file().exists()
            assert revoked_tokens == ["refresh-1"]
        elif action in {"retry", "retry-error"}:
            assert state["connected"] and state["sign_in_error"] is None
            assert json.loads(token_file().read_bytes())["refresh_token"] == "fresh-token"
            assert GoogleAuth().access_token() == "fresh-access"
            assert stat.S_IMODE(token_file().stat().st_mode) == 0o600
            assert revoked_tokens == []
        else:
            assert state["connected"] and token_file().read_bytes() == original
            assert ("cancelled" if action == "cancel" else "in time") in state["sign_in_error"]
            assert revoked_tokens == []


@pytest.mark.parametrize(("failure", "message"), [
    ("denied", "declined"), ("scopes", "allow the requested Calendar and Tasks"),
    ("transport", "retry the connection"), ("malformed", "unexpected"), ("save", "could not be saved"),
])
def test_failed_sign_in_preserves_the_previous_connection(db, monkeypatch, revoked_tokens, caplog, failure, message):
    _signed_in()
    original = token_file().read_bytes()
    setup = client_file().read_bytes()

    def exchange(url, fields):
        if failure == "transport":
            raise GoogleUnavailable("google_unreachable", "Check your internet connection and retry the connection.")
        if failure == "scopes":
            return _tokens("refresh-1", scope=SCOPES[-1])
        if failure == "malformed":
            return _tokens(expires_in={"bad": "secret-canary"})
        assert failure == "save"
        return _tokens()

    def fail_write(path, data):
        raise OSError("secret-canary")

    monkeypatch.setattr(google, "_post_form", exchange)
    if failure == "save":
        monkeypatch.setattr(google, "write_private_file", fail_write)
    with _app(db) as client:
        paused_at = client.post("/api/google/pause").json()["tasks"]["paused_at"]
        link = client.post("/api/google/connect").json()
        callback = {"error": "access_denied", "error_description": "secret-canary"} if failure == "denied" else {"code": "secret-canary"}
        _callback(link["url"], **callback)
        state = _settled(client)
        assert state["connected"] and state["status"] == "paused"
        assert state["tasks"]["paused_at"] == paused_at
        assert state["missing_permissions"] == []
        assert message in state["sign_in_error"]
        assert all(value not in json.dumps(state) for value in ("refresh-1", "fresh-token", "fresh-access", "secret-canary"))
        assert "secret-canary" not in caplog.text
    assert token_file().read_bytes() == original and client_file().read_bytes() == setup
    assert revoked_tokens == []


@pytest.mark.parametrize("action", ["cancel", "timeout"])
def test_waiting_sign_in_ignores_bad_state_and_can_end_with_an_incomplete_socket(db, monkeypatch, action):
    _signed_in()
    now = [100.0]
    monkeypatch.setattr(google, "time", SimpleNamespace(monotonic=lambda: now[0]))

    def unexpected_exchange(*args):
        pytest.fail("The listener must not exchange a code from a rejected callback.")

    monkeypatch.setattr(google, "_post_form", unexpected_exchange)
    with _app(db) as client:
        link = client.post("/api/google/connect").json()
        with pytest.raises(HTTPError) as mismatch:
            _callback(link["url"], code="canary", state="incorrect")
        assert mismatch.value.code == 400
        assert client.get("/api/google").json()["sign_in_attempt_id"] == link["attempt_id"]
        redirect = urlsplit(parse_qs(urlsplit(link["url"]).query)["redirect_uri"][0])
        with socket.create_connection((redirect.hostname, redirect.port), timeout=3) as partial:
            partial.sendall(b"GET /?code=incomplete")
            cancel = {"attempt_id": link["attempt_id"]}
            if action == "cancel":
                for headers, status in (({"Origin": "https://evil.example"}, 403), ({"Host": "evil.example"}, 400)):
                    assert client.post("/api/google/cancel-sign-in", json=cancel, headers=headers).status_code == status
                assert client.get("/api/google").json()["sign_in_attempt_id"] == link["attempt_id"]
                assert client.post("/api/google/cancel-sign-in", json=cancel).json() == {"cancelled": True}
            else:
                now[0] += google.SIGN_IN_WAIT_SECONDS
            state = _settled(client)
            assert state["connected"] and state["sign_in_attempt_id"] is None
            assert ("cancelled" if action == "cancel" else "in time") in state["sign_in_error"]
            # The listener exits while the accepted but incomplete request is still open.
            until = time.monotonic() + 1
            while time.monotonic() < until:
                try:
                    with socket.create_connection((redirect.hostname, redirect.port), timeout=0.1):
                        time.sleep(0.02)
                except ConnectionRefusedError:
                    break
            else:
                pytest.fail("Ended sign-in left its listener open")


def test_automatic_sync_checks_connection_again_under_lock(db):
    def unexpected_client():
        pytest.fail("Disconnected automatic sync must not construct a client")

    service = GoogleSyncService(db, unexpected_client, GoogleUnavailable, lambda: False)
    assert service.sync_now(automatic=True) is None
