"""Durable intents for Google creates. No provider call occurs in a transaction.

This storage primitive is not yet connected to sync. An unresolved intent
represents uncertainty, including a process crash before the request was sent.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from backend.storage.db import Database, utc_now


class PendingCreate(RuntimeError):
    """A prior create has an uncertain remote outcome or the account changed."""


@dataclass(frozen=True)
class CreateIntent:
    operation_id: str
    account_key: str
    resource_kind: str
    local_id: str
    parent_id: str


def pending_for(db: Database, account_key: str) -> CreateIntent | None:
    with db.read() as conn:
        row = conn.execute("SELECT * FROM google_create_intents WHERE account_key = ?", (account_key,)).fetchone()
    return CreateIntent(*(row[k] for k in ("operation_id", "account_key", "resource_kind", "local_id", "parent_id"))) if row else None


def begin(db: Database, account_key: str, resource_kind: str, local_id: str, parent_id: str = "") -> CreateIntent:
    """Save one intent only if the currently adopted account still matches."""
    intent = CreateIntent(str(uuid4()), account_key, resource_kind, local_id, parent_id)
    with db.write() as conn:
        owner = conn.execute("SELECT account_key FROM google_sync WHERE id = 1").fetchone()
        if not owner or owner["account_key"] != account_key:
            raise PendingCreate("Google account changed before the create could start.")
        if conn.execute("SELECT 1 FROM google_create_intents WHERE account_key = ?", (account_key,)).fetchone():
            raise PendingCreate("A previous Google create needs review before syncing this account.")
        conn.execute("INSERT INTO google_create_intents VALUES (?, ?, ?, ?, ?, ?)",
                     (intent.operation_id, account_key, resource_kind, local_id, parent_id, utc_now()))
    return intent


def publish(db: Database, intent: CreateIntent, save_mapping: Callable[[sqlite3.Connection], None]) -> None:
    """Atomically save the mapping and remove the exact intent, or retain both old states."""
    with db.write() as conn:
        owner = conn.execute("SELECT account_key FROM google_sync WHERE id = 1").fetchone()
        row = conn.execute("SELECT * FROM google_create_intents WHERE operation_id = ?", (intent.operation_id,)).fetchone()
        if (not owner or owner["account_key"] != intent.account_key or not row
                or any(row[k] != getattr(intent, k) for k in ("account_key", "resource_kind", "local_id", "parent_id"))):
            raise PendingCreate("Google account or create intent changed; review is required.")
        save_mapping(conn)
        conn.execute("DELETE FROM google_create_intents WHERE operation_id = ?", (intent.operation_id,))
