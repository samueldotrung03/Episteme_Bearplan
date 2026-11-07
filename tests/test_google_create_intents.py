"""Disposable persistence tests; no Google connection or personal data."""
import sqlite3

import pytest

from backend.domain.google_create_intents import PendingCreate, begin, pending_for, publish
from backend.storage.db import open_database

ACCOUNT_A = "a" * 32
ACCOUNT_B = "b" * 32


def set_account(db, value):
    with db.write() as conn:
        conn.execute("INSERT INTO google_sync (id, account_key) VALUES (1, ?) "
                     "ON CONFLICT(id) DO UPDATE SET account_key = excluded.account_key", (value,))


def test_intent_survives_restart_and_account_switch(db):
    set_account(db, ACCOUNT_A)
    intent = begin(db, ACCOUNT_A, "task", "local-id", "parent-id")
    reopened = open_database(db.path)
    assert pending_for(reopened, ACCOUNT_A) == intent
    set_account(reopened, ACCOUNT_B)
    with pytest.raises(PendingCreate):
        publish(reopened, intent, lambda conn: pytest.fail("must not publish"))
    set_account(reopened, ACCOUNT_A)
    with pytest.raises(PendingCreate):
        begin(reopened, ACCOUNT_A, "event", "other-id")
    assert pending_for(reopened, ACCOUNT_A) == intent


def test_mapping_and_resolution_commit_together_or_roll_back(db):
    set_account(db, ACCOUNT_A)
    intent = begin(db, ACCOUNT_A, "task_list", "project-id")
    def fail(conn):
        conn.execute("UPDATE google_sync SET last_error = 'temporary' WHERE id = 1")
        raise OSError("injected failure")
    with pytest.raises(OSError):
        publish(db, intent, fail)
    assert pending_for(db, ACCOUNT_A) == intent
    with db.read() as conn:
        assert conn.execute("SELECT last_error FROM google_sync WHERE id = 1").fetchone()[0] is None
    publish(db, intent, lambda conn: conn.execute("UPDATE google_sync SET last_error = 'saved' WHERE id = 1"))
    assert pending_for(db, ACCOUNT_A) is None
    with db.read() as conn:
        assert conn.execute("SELECT last_error FROM google_sync WHERE id = 1").fetchone()[0] == "saved"
    with pytest.raises(PendingCreate):
        publish(db, intent, lambda conn: pytest.fail("must not replay"))


def test_intent_rejects_unverified_account_and_invalid_kind(db):
    with pytest.raises(PendingCreate):
        begin(db, ACCOUNT_A, "task", "local-id")
    set_account(db, ACCOUNT_A)
    with pytest.raises(sqlite3.IntegrityError):
        begin(db, ACCOUNT_A, "unknown", "local-id")
    assert pending_for(db, ACCOUNT_A) is None


def test_upgrade_failure_preserves_prior_database_and_retries(tmp_path):
    from dataclasses import replace
    from backend.storage.db import Database
    from backend.storage.migrations import MigrationError, current_version, load_migrations, migrate

    path = tmp_path / "upgrade.sqlite3"
    old = Database(path)
    migrations = load_migrations()
    assert migrate(old, migrations[:22]) == 22
    set_account(old, ACCOUNT_A)
    broken = list(migrations)
    broken[22] = replace(broken[22], sql=broken[22].sql + "\nSELECT * FROM missing_fault_table;")
    with pytest.raises(MigrationError):
        migrate(old, broken)
    assert current_version(old) == 22
    with old.read() as conn:
        assert conn.execute("SELECT account_key FROM google_sync WHERE id = 1").fetchone()[0] == ACCOUNT_A
        assert conn.execute("SELECT name FROM sqlite_master WHERE name = 'google_create_intents'").fetchone() is None
    upgraded = open_database(path)
    intent = begin(upgraded, ACCOUNT_A, "calendar", "bearplans")
    assert pending_for(open_database(path), ACCOUNT_A) == intent
