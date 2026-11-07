"""Uncertain Google creates never repeat without explicit account-bound review."""
from datetime import date, timedelta

import pytest

from backend.domain import google_calendar, google_tasks
from backend.domain.google_account import account_key
from backend.domain.google_create_intents import pending_for
from backend.domain.planning import create_placement, set_placement_time
from backend.domain.projects import create_project
from backend.domain.tasks import create_task, remove_subtask
from backend.platform.google import GoogleUnavailable
from backend.storage.db import open_database
from tests.test_google_account import Account


def prepare(db, kind):
    provider = Account("guard@example.com")
    google_tasks.sync(db, provider.tasks, GoogleUnavailable, provider)
    if kind == "task_list":
        create_project(db, "Synthetic project")
    elif kind == "task":
        create_task(db, "Synthetic task")
    else:
        if kind == "event":
            seed = create_task(db, "Seed calendar")
            set_placement_time(db, create_placement(db, seed.id, date.today() + timedelta(days=2)).id, "12:00")
            google_tasks.sync(db, provider.tasks, GoogleUnavailable, provider)
        task = create_task(db, "Synthetic event")
        set_placement_time(db, create_placement(db, task.id, date.today() + timedelta(days=3)).id, "13:00")
    return provider


@pytest.mark.parametrize("kind", ["task_list", "task", "calendar", "event"])
@pytest.mark.parametrize("failure", ["lost_response", "mapping_failure", "malformed_response"])
def test_uncertain_create_is_durable_and_blocks_all_sync_writes(db, monkeypatch, kind, failure):
    provider = prepare(db, kind)
    owner = account_key(provider)
    module = google_tasks if kind in ("task_list", "task") else google_calendar
    target = provider.tasks if kind in ("task_list", "task") else provider
    method = {"task_list": "insert_list", "task": "insert_task", "calendar": "insert_calendar", "event": "insert_event"}[kind]
    original_insert = getattr(target, method)
    original_publish = module.publish
    with monkeypatch.context() as patch:
        if failure in ("lost_response", "malformed_response"):
            def ambiguous(*args, **kwargs):
                original_insert(*args, **kwargs)
                if failure == "lost_response":
                    raise GoogleUnavailable("google_unreachable", "Lost response")
                return {}
            patch.setattr(target, method, ambiguous)
            expected = GoogleUnavailable
        else:
            def fail_mapping(db, intent, save):
                if intent.resource_kind != kind:
                    return original_publish(db, intent, save)
                def fail_after_write(conn):
                    save(conn)
                    raise OSError("injected mapping failure")
                return original_publish(db, intent, fail_after_write)
            patch.setattr(module, "publish", fail_mapping)
            expected = GoogleUnavailable
        with pytest.raises(expected) as failed:
            google_tasks.sync(db, provider.tasks, GoogleUnavailable, provider)
        assert failed.value.code == "google_create_review_required"
        if kind in ("calendar", "event"):
            assert "Google Tasks finished" in failed.value.message
    pending = pending_for(open_database(db.path), owner)
    assert pending is not None and pending.resource_kind == kind
    task_calls, calendar_calls = list(provider.tasks.calls), list(provider.calls)
    with pytest.raises(GoogleUnavailable) as blocked:
        google_tasks.sync(open_database(db.path), provider.tasks, GoogleUnavailable, provider)
    assert blocked.value.code == "google_create_review_required"
    assert provider.tasks.calls == task_calls and provider.calls == calendar_calls
    assert pending_for(db, owner) == pending


def test_intent_write_failure_makes_no_provider_create(db, monkeypatch):
    provider = prepare(db, "task")
    before = list(provider.tasks.calls)
    def fail(*args, **kwargs):
        raise OSError("intent storage unavailable")
    monkeypatch.setattr(google_tasks, "begin", fail)
    with pytest.raises(GoogleUnavailable) as error:
        google_tasks.sync(db, provider.tasks, GoogleUnavailable, provider)
    assert error.value.code == "google_storage_unavailable"
    assert provider.tasks.calls == before


def test_removed_subtask_during_remote_create_retains_intent(db, monkeypatch):
    provider = Account("guard@example.com")
    parent = create_task(db, "Parent")
    google_tasks.sync(db, provider.tasks, GoogleUnavailable, provider)
    child = create_task(db, "Child", parent_id=parent.id)
    original = provider.tasks.insert_task
    def create_then_remove(*args, **kwargs):
        result = original(*args, **kwargs)
        remove_subtask(db, child.id)
        return result
    monkeypatch.setattr(provider.tasks, "insert_task", create_then_remove)
    with pytest.raises(GoogleUnavailable, match="changed") as failed:
        google_tasks.sync(db, provider.tasks, GoogleUnavailable, provider)
    assert failed.value.code == "google_create_review_required"
    assert pending_for(db, account_key(provider)).local_id == child.id


def test_unresolved_account_intent_survives_switch_away_and_back(db):
    from backend.domain.google_account import adopt_other_account, check_account
    from backend.domain.google_create_intents import begin
    from backend.domain.google_tasks import get_status

    first = Account("first@example.com")
    second = Account("second@example.com")
    google_tasks.sync(db, first.tasks, GoogleUnavailable, first)
    first_key, second_key = account_key(first), account_key(second)
    intent = begin(db, first_key, "task", "missing-local")
    with pytest.raises(GoogleUnavailable):
        check_account(db, second, GoogleUnavailable)
    adopt_other_account(db, get_status(db, second_key).account_review_key, second_key)
    google_tasks.sync(db, second.tasks, GoogleUnavailable, second)
    assert pending_for(db, first_key) == intent
    with pytest.raises(GoogleUnavailable):
        check_account(db, first, GoogleUnavailable)
    adopt_other_account(db, get_status(db, first_key).account_review_key, first_key)
    calls = list(first.tasks.calls)
    with pytest.raises(GoogleUnavailable, match="review"):
        google_tasks.sync(open_database(db.path), first.tasks, GoogleUnavailable, first)
    assert first.tasks.calls == calls and pending_for(db, first_key) == intent


def test_automatic_sync_after_restart_stops_before_provider_writes(db):
    from backend.domain.google_create_intents import begin
    from backend.domain.google_tasks import GoogleSyncService

    provider = prepare(db, "task")
    owner = account_key(provider)
    begin(db, owner, "task", "missing-local")
    calls = list(provider.tasks.calls), list(provider.calls)
    service = GoogleSyncService(open_database(db.path), lambda: provider.tasks, GoogleUnavailable,
                                lambda: True, lambda: provider)
    with pytest.raises(GoogleUnavailable) as error:
        service.sync_now(automatic=True)
    assert error.value.code == "google_create_review_required"
    assert (provider.tasks.calls, provider.calls) == calls


def test_final_status_write_failure_keeps_completed_mappings_and_retries_without_duplicates(db, monkeypatch):
    provider = prepare(db, "task")
    original = google_tasks._set_sync
    def fail_success(db, *, success, error):
        if success:
            raise OSError("injected status failure")
        return original(db, success=success, error=error)
    with monkeypatch.context() as patch:
        patch.setattr(google_tasks, "_set_sync", fail_success)
        with pytest.raises(GoogleUnavailable) as error:
            google_tasks.sync(db, provider.tasks, GoogleUnavailable, provider)
        assert error.value.code == "google_storage_unavailable"
    count = provider.tasks.calls.count("insert_task")
    google_tasks.sync(db, provider.tasks, GoogleUnavailable, provider)
    assert provider.tasks.calls.count("insert_task") == count


def test_pending_intent_is_visible_to_a_fresh_process(db):
    import subprocess
    import sys
    from backend.domain.google_create_intents import begin

    provider = prepare(db, "task")
    owner = account_key(provider)
    intent = begin(db, owner, "task", "synthetic-local")
    code = (
        "import sys; from pathlib import Path; "
        "from backend.storage.db import open_database; "
        "from backend.domain.google_create_intents import pending_for; "
        "value = pending_for(open_database(Path(sys.argv[1])), sys.argv[2]); "
        "assert value is not None and value.operation_id == sys.argv[3]"
    )
    result = subprocess.run([sys.executable, "-c", code, str(db.path), owner, intent.operation_id],
                            capture_output=True, text=True, timeout=15, check=False)
    assert result.returncode == 0, result.stderr


def test_sync_refuses_to_write_without_fresh_account_verification(db):
    from tests.test_google_tasks import FakeTasks

    fake = FakeTasks()
    create_task(db, "Synthetic task")
    with pytest.raises(GoogleUnavailable) as error:
        google_tasks.sync(db, fake, GoogleUnavailable)
    assert error.value.code == "google_account_unverified"
    assert fake.calls == []


def test_status_storage_failure_still_returns_structured_error(db, monkeypatch):
    provider = prepare(db, "task")
    def fail_status(*args, **kwargs):
        raise OSError("storage unavailable")
    with monkeypatch.context() as patch:
        patch.setattr(google_tasks, "_set_sync", fail_status)
        with pytest.raises(GoogleUnavailable) as error:
            google_tasks.sync(db, provider.tasks, GoogleUnavailable, provider)
        assert error.value.code == "google_storage_unavailable"
    before = provider.tasks.calls.count("insert_task")
    google_tasks.sync(db, provider.tasks, GoogleUnavailable, provider)
    assert provider.tasks.calls.count("insert_task") == before
