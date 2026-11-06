"""Protect Google mappings and cached data with the verified account's primary calendar."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any, Protocol

from backend.domain.errors import InvalidInput
from backend.storage.db import Database

OTHER_ACCOUNT_CODE = "google_other_account"
OTHER_ACCOUNT_MESSAGE = (
    "You are signed in to a different Google account than the one BearPlans syncs with. "
    "Sign in to the previous account, or review starting fresh with this one.")
UNVERIFIED_ACCOUNT_CODE = "google_account_unverified"
UNVERIFIED_ACCOUNT_MESSAGE = "BearPlans could not verify your Google account. Reconnect Google and try again."
ACCOUNT_LINK_TABLES = ("google_tasks", "google_task_lists", "google_events", "google_calendar",
                       "google_source_events", "google_source_calendars")


class CalendarLister(Protocol):
    def calendar_list(self) -> list[dict[str, Any]]: ...


def account_key(client: CalendarLister) -> str | None:
    primaries = [item.get("id") for item in client.calendar_list() if item.get("primary") is True]
    if len(primaries) != 1 or not isinstance(primaries[0], str) or not primaries[0].strip():
        return None
    primary = primaries[0].strip().lower()
    return hashlib.sha256(f"bearplans-google-account:{primary}".encode()).hexdigest()[:32]


def verify_account(client: CalendarLister, unavailable: type[Exception]) -> str:
    key = account_key(client)
    if key is None:
        raise unavailable(UNVERIFIED_ACCOUNT_CODE, UNVERIFIED_ACCOUNT_MESSAGE)
    return key


def cache_owner(db: Database, *, connected: bool, verified_key: str | None) -> str | None:
    with db.read() as conn:
        row = conn.execute("SELECT account_key FROM google_sync WHERE id = 1").fetchone()
    owner = row["account_key"] if row else None
    return owner if not connected or owner == verified_key else None


def check_account(db: Database, client: CalendarLister, unavailable: type[Exception],
                  remember: Callable[[str], None] | None = None) -> None:
    key = verify_account(client, unavailable)
    if remember is not None:
        remember(key)
    with db.write() as conn:
        conn.execute("INSERT INTO google_sync (id) VALUES (1) ON CONFLICT(id) DO NOTHING")
        owner = conn.execute("SELECT account_key FROM google_sync WHERE id = 1").fetchone()["account_key"]
        unowned_links = owner is None and any(
            conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() is not None
            for table in (*ACCOUNT_LINK_TABLES, "google_event_tasks")
        )
        if owner == key or (owner is None and not unowned_links):
            conn.execute("UPDATE google_sync SET account_key = ?, other_account_key = NULL WHERE id = 1", (key,))
            return
        conn.execute("UPDATE google_sync SET other_account_key = ? WHERE id = 1", (key,))
    if unowned_links:
        raise unavailable(
            "google_account_review_required",
            "The saved Google links have no verified owner. Review starting fresh before syncing this account.",
        )
    raise unavailable(OTHER_ACCOUNT_CODE, OTHER_ACCOUNT_MESSAGE)


def account_review_key(owner: str | None, candidate: str) -> str:
    return hashlib.sha256(f"bearplans-google-review:{owner or ''}:{candidate}".encode()).hexdigest()[:32]


def adopt_other_account(db: Database, reviewed_key: str, current_key: str) -> None:
    """After fresh verification, forget the reviewed old links locally in one write."""
    with db.write() as conn:
        row = conn.execute("SELECT account_key, other_account_key FROM google_sync WHERE id = 1").fetchone()
        if (row is None or row["other_account_key"] != current_key
                or account_review_key(row["account_key"], current_key) != reviewed_key):
            raise InvalidInput("account", "The Google account changed or was already accepted. Refresh and review again.")
        for table in ACCOUNT_LINK_TABLES:
            conn.execute(f"DELETE FROM {table}")
        conn.execute("UPDATE google_sync SET account_key = ?, other_account_key = NULL, "
                     "last_error = NULL, last_success_at = NULL, last_attempt_at = NULL WHERE id = 1", (current_key,))
