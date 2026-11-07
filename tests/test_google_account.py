"""Another Google account never reuses the links made in the account BearPlans syncs with."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.domain.google_account import account_key
from backend.domain.google_tasks import get_status, sync
from backend.domain.planning import create_placement, set_placement_time
from backend.domain.projects import create_project
from backend.domain.tasks import create_task, get_task
from backend.platform import google
from backend.platform.google import GoogleUnavailable, token_file
from backend.storage.db import Database, open_database
from backend.storage.migrations import MigrationError, current_version, load_migrations, migrate
from tests.test_google_controls import _callback, _signed_in, _settled, _tokens
from tests.test_google_calendar import DAY, FakeCalendar
from tests.test_google_tasks import FakeTasks


class Account(FakeCalendar):
    """One Google account: its Tasks, its calendars, and its primary calendar ID."""

    def __init__(self, email: str) -> None:
        super().__init__()
        self.email = email
        self.tasks = FakeTasks()

    def calendar_list(self):
        return [{"id": self.email, "summary": "Me", "primary": True},
                *({"id": cid, "summary": name} for cid, name in self.names.items())]

    def list_events(self, calendar_id, time_min, time_max):
        return []


def _work(db):
    project = create_project(db, "MATH 54")
    task = create_task(db, "Problem set", project_id=project.id, estimate_minutes=60)
    set_placement_time(db, create_placement(db, task.id, DAY).id, "14:00")


def _counts(db):
    with db.read() as conn:
        return {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("google_task_lists", "google_tasks", "google_events", "google_calendar")}


def test_first_account_is_adopted_and_only_a_hash_is_stored(db):
    _work(db)
    first = Account("Me@Example.com")
    sync(db, first.tasks, GoogleUnavailable, first)
    with db.read() as conn:
        row = conn.execute("SELECT account_key, other_account_key FROM google_sync").fetchone()
    assert row["account_key"] == account_key(Account("me@example.com")) and row["other_account_key"] is None
    assert "@" not in row["account_key"] and "example" not in row["account_key"]
    links = _counts(db)
    assert links["google_tasks"] == links["google_events"] == links["google_calendar"] == 1
    sync(db, first.tasks, GoogleUnavailable, first)  # Same account: carries on, nothing duplicated.
    assert _counts(db) == links


def test_another_account_stops_before_touching_google_until_the_user_chooses(db):
    _work(db)
    first, second = Account("me@example.com"), Account("other@example.com")
    sync(db, first.tasks, GoogleUnavailable, first)
    links = _counts(db)
    with pytest.raises(GoogleUnavailable) as raised:
        sync(db, second.tasks, GoogleUnavailable, second)
    assert raised.value.code == "google_other_account"
    assert second.tasks.calls == [] and second.calls == []  # Nothing was created in the other account.
    assert _counts(db) == links
    status = get_status(db, account_key(second))
    assert status.other_account and "different Google account" in (status.last_error or "")

    # Signing back in to the first account carries on as before.
    lists = first.tasks.calls.count("insert_list")
    sync(db, first.tasks, GoogleUnavailable, first)
    status = get_status(db, account_key(first))
    assert status.account_status == "verified" and not status.other_account and status.last_error is None
    assert first.tasks.calls.count("insert_list") == lists and _counts(db) == links  # No duplicates.


def test_use_this_account_starts_fresh_in_the_new_account(db):
    _work(db)
    first, second = Account("me@example.com"), Account("other@example.com")
    sync(db, first.tasks, GoogleUnavailable, first)
    with pytest.raises(GoogleUnavailable):
        sync(db, second.tasks, GoogleUnavailable, second)
    _signed_in()
    with TestClient(create_app(db, google_tasks_client=second.tasks, google_calendar_client=second),
                    base_url="http://127.0.0.1:8765") as client:
        assert client.post("/api/google/calendars/refresh").status_code == 502
        pending = client.get("/api/google").json()["tasks"]
        review = pending["account_review_key"]
        assert review and pending["account_status"] == "different_account"
        state = client.post("/api/google/use-this-account", json={"review_key": review}).json()
        assert state["connection_changing"] is False
        assert state["tasks"]["account_status"] == "verified"
        assert state["tasks"]["other_account"] is False and state["tasks"]["last_error"] is None
        assert client.post("/api/google/use-this-account", json={"review_key": review}).status_code == 422
    # The background sync may already have run after the switch; either way each list,
    # task and the BearPlans calendar is created once in the new account.
    sync(db, second.tasks, GoogleUnavailable, second)
    assert second.tasks.calls.count("insert_list") == first.tasks.calls.count("insert_list")
    assert second.tasks.calls.count("insert_task") == 1 and second.calls.count("insert_calendar") == 1
    assert len(second.live()) == 1
    assert len(first.live()) == 1  # The first account was left as it was.
    with pytest.raises(GoogleUnavailable):  # Now the first account is the "other" one.
        sync(db, first.tasks, GoogleUnavailable, first)


def test_calendar_verification_is_separate_from_full_sync_success(db):
    first = Account("account-private@example.com")
    _signed_in()
    with TestClient(create_app(db, google_tasks_client=first.tasks, google_calendar_client=first),
                    base_url="http://127.0.0.1:8765") as client:
        client.post("/api/google/calendars/refresh").raise_for_status()
        verified = client.get("/api/google").json()
        assert verified["tasks"]["account_status"] == "verified"
        assert verified["status"] == "not_synced" and verified["tasks"]["last_success_at"] is None
        synced = client.post("/api/google/tasks/sync").json()
        assert synced["status"] == "working" and synced["tasks"]["last_success_at"]
        response = client.get("/api/google")
        assert first.email not in response.text and account_key(first) not in response.text


def test_calendar_reading_routes_check_the_account_too(db):
    first, second = Account("me@example.com"), Account("other@example.com")
    sync(db, first.tasks, GoogleUnavailable, first)
    _signed_in()
    with TestClient(create_app(db, google_tasks_client=second.tasks, google_calendar_client=second),
                    base_url="http://127.0.0.1:8765") as client:
        response = client.post("/api/google/calendars/refresh")
        assert response.status_code == 502 and response.json()["error"]["code"] == "google_other_account"
        assert client.get("/api/google").json()["tasks"]["other_account"] is True


@pytest.mark.parametrize("primary", [[], [{"id": "x"}], [{"id": " ", "primary": True}],
                                      [{"id": "x", "primary": True}, {"id": "y", "primary": True}]])
def test_unverified_account_cannot_use_links(db, primary):
    first = Account("me@example.com")
    _work(db)
    sync(db, first.tasks, GoogleUnavailable, first)
    unknown = Account("other@example.com")
    unknown.calendar_list = lambda: primary
    with pytest.raises(GoogleUnavailable) as raised:
        sync(db, unknown.tasks, GoogleUnavailable, unknown)
    assert raised.value.code == "google_account_unverified"
    assert unknown.calls == unknown.tasks.calls == []


def test_reconnect_keeps_account_cache_and_imports_isolated(db, monkeypatch):
    from tests.test_google_reading import D1, FakeReader

    _signed_in()
    accounts = {"a": FakeReader(), "b": FakeReader(), "c": FakeReader()}
    for name, fake in accounts.items():
        fake.calendars[0]["id"] = f"{name}@example.com"
        fake.events["work@group"][0]["summary"] = f"Event for {name}"
        fake.events["work@group"][0]["start"] = {"date": D1}
        fake.events["work@group"][0]["end"] = {"date": D1}

    class Reader:
        def __init__(self, auth):
            self.auth = auth

        def calendar_list(self):
            return accounts[self.auth.access_token()].calendar_list()

        def list_events(self, *args):
            return accounts[self.auth.access_token()].list_events(*args)

    from backend import app as app_module

    monkeypatch.setattr(app_module, "GoogleCalendarClient", Reader)
    monkeypatch.setattr(google, "_post_form", lambda url, fields: (
        _tokens(fields["code"], access_token=fields["code"])
        if "code" in fields else _tokens(access_token={"refresh-1": "a"}.get(fields["refresh_token"], fields["refresh_token"]))
    ))

    def app():
        return TestClient(create_app(open_database(db.path)), base_url="http://127.0.0.1:8765")

    def reconnect(client, account):
        link = client.post("/api/google/connect").json()
        _callback(link["url"], code=account)
        assert _settled(client)["sign_in_error"] is None

    client = app()
    calendars = client.post("/api/google/calendars/refresh").json()
    owner = calendars[0]["account_key"]
    choice = {"account_key": owner, "calendar_ids": ["work@group"]}
    assert client.put("/api/google/calendars", json=choice).status_code == 200
    event_query = f"/api/google/events?start={D1}&end={D1}"
    event_a = {"account_key": owner, "calendar_id": "work@group", "event_id": "w"}
    task_a = client.post("/api/google/events/add", json=event_a).json()["task"]
    assert app().get(event_query).json()[0]["task_id"] == task_a["id"]

    reconnect(client, "b")
    restarted = app()
    assert restarted.get(event_query).json() == []
    assert restarted.get("/api/google/calendars").json() == []
    assert restarted.get(f"/api/planning?week={D1}").json()["calendar_events"] == []
    assert restarted.post("/api/google/events/add", json=event_a).status_code == 409
    assert restarted.post("/api/google/calendars/refresh").json()["error"]["code"] == "google_other_account"
    review = restarted.get("/api/google").json()["tasks"]["account_review_key"]
    assert review
    reconnect(restarted, "c")
    assert app().post("/api/google/use-this-account", json={"review_key": review}).status_code == 422

    reconnect(restarted, "a")
    assert restarted.post("/api/google/calendars/refresh").status_code == 200
    assert restarted.get(event_query).json()[0]["task_id"] == task_a["id"]

    reconnect(restarted, "b")
    assert restarted.post("/api/google/calendars/refresh").status_code == 502
    review = restarted.get("/api/google").json()["tasks"]["account_review_key"]
    assert restarted.post("/api/google/use-this-account", json={"review_key": review},
                          headers={"Origin": "https://evil.example"}).status_code == 403
    assert restarted.post("/api/google/use-this-account", json={"review_key": review}).status_code == 200
    calendars_b = app().post("/api/google/calendars/refresh").json()
    new_key = calendars_b[0]["account_key"]
    assert new_key != owner
    assert restarted.put("/api/google/calendars", json=choice).status_code == 409
    assert restarted.put("/api/google/calendars", json={**choice, "account_key": new_key}).status_code == 200
    assert restarted.post("/api/google/events/add", json=event_a).status_code == 409
    event_b = {**event_a, "account_key": new_key}
    task_b = restarted.post("/api/google/events/add", json=event_b).json()["task"]
    assert task_a["id"] != task_b["id"] and task_b["title"] == "Event for b"
    assert get_task(db, task_a["id"]).title == "Event for a"
    assert app().post("/api/google/events/add", json=event_b).json()["task"]["id"] == task_b["id"]


@pytest.mark.parametrize("version", [20, 21])
def test_upgrade_quarantines_unowned_imports_without_reusing_links(tmp_path, version):
    path = tmp_path / "upgrade.sqlite3"
    old = Database(path)
    assert migrate(old, load_migrations()[:version]) == version
    task = create_task(old, "Legacy import")
    with old.write() as conn:
        conn.execute("INSERT INTO google_event_tasks (calendar_id, event_id, task_id, created_at) "
                     "VALUES ('shared', 'event', ?, '2026-11-05T00:00:00Z')", (task.id,))
    if version == 21:
        migrations = load_migrations()
        new_migration = migrations[version]
        migrations[version] = replace(new_migration, sql=new_migration.sql + "\nSELECT * FROM missing_fault_table;")
        with pytest.raises(MigrationError, match="rolled back"):
            migrate(old, migrations)
        assert current_version(old) == version
        with old.read() as conn:
            assert conn.execute("SELECT task_id FROM google_event_tasks").fetchone()["task_id"] == task.id
    upgraded = open_database(path)
    account = Account("new@example.com")
    with pytest.raises(GoogleUnavailable) as raised:
        sync(upgraded, account.tasks, GoogleUnavailable, account)
    assert raised.value.code == "google_account_review_required"
    assert account.calls == account.tasks.calls == []
    with open_database(path).read() as conn:
        row = conn.execute("SELECT account_key, task_id FROM google_event_tasks").fetchone()
        assert (row["account_key"], row["task_id"]) == ("", task.id)
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert get_task(upgraded, task.id) == task


def test_oauth_publication_waits_for_active_google_operation(db, monkeypatch):
    _signed_in()
    original = token_file().read_bytes()
    ready, release = Event(), Event()
    client = TestClient(create_app(db), base_url="http://127.0.0.1:8765")
    service = client.app.state.google_sync
    original_publish = service.publish_authorization

    def publish(action):
        ready.set()
        original_publish(action)

    monkeypatch.setattr(service, "publish_authorization", publish)
    monkeypatch.setattr(google, "_post_form", lambda url, fields: _tokens("replacement"))
    with ThreadPoolExecutor(max_workers=1) as pool:
        entered = Event()

        def operation():
            entered.set()
            assert release.wait(5)

        active = pool.submit(service.while_idle, operation)
        try:
            assert entered.wait(3)
            link = client.post("/api/google/connect").json()
            _callback(link["url"], code="new")
            assert ready.wait(3)
            assert client.get("/api/google").json()["sign_in_pending"]
            assert token_file().read_bytes() == original
        finally:
            release.set()
        active.result(4)
    assert _settled(client)["sign_in_error"] is None
    assert token_file().read_bytes() != original


def test_reviewed_create_resolution_requires_current_account_and_exact_review(db):
    from backend.domain.google_create_intents import begin, pending_for, review_key

    first, other = Account("me@example.com"), Account("other@example.com")
    sync(db, first.tasks, GoogleUnavailable, first)
    owner = account_key(first)
    assert owner is not None
    intent = begin(db, owner, "task", "local-task")
    _signed_in()
    app = create_app(db, google_tasks_client=first.tasks, google_calendar_client=first)
    client = TestClient(app, base_url="http://127.0.0.1:8765")
    before = client.get("/api/google").json()
    assert before["tasks"]["pending_create_unverified"] is True
    assert before["tasks"]["pending_create"] is None
    assert client.post("/api/google/verify-pending-create").status_code == 200
    status = client.get("/api/google").json()
    assert status["tasks"]["pending_create"] == {"kind": "task", "review_key": review_key(intent), "context": "This local item is no longer available"}
    assert status["status"] == "needs_attention"
    assert client.post("/api/google/resolve-uncertain-create", json={"review_key": review_key(intent)}).status_code == 422
    assert client.post("/api/google/resolve-uncertain-create", json={"review_key": "0" * 32, "accept_possible_duplicate": True}).status_code == 409
    app.state.google_calendar_factory = lambda: other
    assert client.post("/api/google/resolve-uncertain-create", json={"review_key": review_key(intent), "accept_possible_duplicate": True}).status_code == 409
    assert pending_for(db, owner) == intent
    app.state.google_calendar_factory = lambda: first
    payload = {"review_key": review_key(intent), "accept_possible_duplicate": True}
    assert client.post("/api/google/resolve-uncertain-create", json=payload).status_code == 200
    assert pending_for(db, owner) is None
    replacement = begin(db, owner, "task", "local-task")
    assert client.post("/api/google/resolve-uncertain-create", json=payload).status_code == 409
    assert pending_for(db, owner) == replacement
