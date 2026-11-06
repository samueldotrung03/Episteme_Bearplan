"""Google routes: status, sign-in, disconnect, sync, followed calendars and their events.

Tokens and the client secret are never returned; only whether they exist.
Sync calls Google outside any transaction (sync route, worker thread).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from backend.domain.google_reading import (
    AddedEvent, SourceCalendar, SourceEvent, add_event_task, list_calendars, list_events, read_calendars,
    refresh_events, set_followed,
)
from backend.domain.google_account import (
    adopt_other_account, cache_owner, check_account, verify_account,
)
from backend.domain.google_tasks import ProviderActivity, SyncStatus, get_status
from backend.platform import google
from backend.platform.google import NOT_CONNECTED, GoogleSetup, GoogleUnavailable

router = APIRouter(prefix="/api/google")


ConnectionStatus = Literal[
    "not_set_up", "signed_out", "signing_in", "needs_attention", "pausing", "paused", "syncing", "not_synced", "working",
]


class GoogleState(BaseModel):
    setup: GoogleSetup
    activity: ProviderActivity
    connection_changing: bool
    pausing: bool
    configured: bool
    connected: bool
    sign_in_pending: bool
    sign_in_attempt_id: str | None
    sign_in_error: str | None
    missing_permissions: list[str]
    tasks: SyncStatus
    # A compact summary for existing callers. Settings can show each dimension separately.
    status: ConnectionStatus
    # On Disconnect, true means Google acknowledged the revocation.
    # False means unconfirmed, and None means there was no saved grant.
    revoked: bool | None = None


class SignIn(BaseModel):
    url: str
    attempt_id: str


class CancelSignIn(BaseModel):
    attempt_id: StrictStr = Field(min_length=1, max_length=64)


class CancelSignInResult(BaseModel):
    cancelled: bool


def _state(request: Request, revoked: bool | None = None) -> GoogleState:
    app = request.app.state
    auth = app.google_auth.authorization_status()
    pausing = app.google_sync.pausing
    activity = app.google_sync.activity
    changing = app.google_sync.connection_changing
    tasks = get_status(app.db, auth.verified_key).model_copy(update={"syncing": activity == "syncing"})
    configured = auth.setup == "configured"
    status: ConnectionStatus
    if pausing:
        status = "pausing"
    elif not configured:
        status = "not_set_up"
    elif auth.attempt_id is not None:
        status = "signing_in"
    elif not auth.connected:
        status = "signed_out"
    elif tasks.last_error or tasks.other_account or auth.missing_permissions:
        status = "needs_attention"
    elif tasks.paused_at:
        status = "paused"
    elif tasks.syncing:
        status = "syncing"
    elif changing or tasks.account_status != "verified" or not tasks.last_success_at:
        status = "not_synced"
    else:
        status = "working"
    return GoogleState(
        setup=auth.setup, activity=activity, connection_changing=changing, pausing=pausing,
        configured=configured, connected=auth.connected, sign_in_pending=auth.attempt_id is not None,
        sign_in_attempt_id=auth.attempt_id, sign_in_error=auth.sign_in_error,
        missing_permissions=auth.missing_permissions, tasks=tasks, status=status, revoked=revoked)


def disconnect_google(request: Request) -> bool | None:
    """Sign out while the caller excludes new Google work and sign-in attempts."""
    state = request.app.state
    try:
        refresh = state.google_sync.while_idle(state.google_auth.disconnect_local)
    except OSError:
        raise HTTPException(
            503, "BearPlans could not remove the Google sign-in. Check folder permissions, then try again."
        ) from None
    return google.revoke_token(refresh) if refresh else None


@router.get("")
def google_state(request: Request) -> GoogleState:
    return _state(request)


class Changes(BaseModel):
    version: int


@router.get("/changes")
def google_changes(request: Request) -> Changes:
    """Cheap check for the open page: refresh when this number changes."""
    return Changes(version=request.app.state.google_sync.version)


@router.post("/connect")
def google_connect(request: Request) -> SignIn:
    state = request.app.state
    with state.google_sync.connection_lock:
        url, attempt_id = state.google_auth.start_sign_in(state.google_sync.publish_authorization)
        return SignIn(url=url, attempt_id=attempt_id)


@router.post("/cancel-sign-in")
def google_cancel_sign_in(body: CancelSignIn, request: Request) -> CancelSignInResult:
    cancelled = request.app.state.google_auth.cancel_sign_in(body.attempt_id)
    return CancelSignInResult(cancelled=cancelled)


@router.post("/disconnect")
def google_disconnect(request: Request) -> GoogleState:
    with request.app.state.google_sync.changing_connection():
        result = _state(request, revoked=disconnect_google(request))
    return result.model_copy(update={"connection_changing": False})


@router.post("/pause")
def google_pause(request: Request) -> GoogleState:
    return request.app.state.google_sync.change_pause(True, lambda: _state(request))


class AccountReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_key: StrictStr = Field(pattern=r"^[0-9a-f]{32}$")


@router.post("/use-this-account")
def google_use_this_account(body: AccountReview, request: Request) -> GoogleState:
    state = request.app.state

    def adopt() -> None:
        reader = state.google_calendar_factory()
        if reader is None:
            raise NOT_CONNECTED
        current = verify_account(reader, GoogleUnavailable)
        state.google_auth.remember_account(current)
        adopt_other_account(state.db, body.review_key, current)

    with state.google_sync.changing_connection():
        state.google_sync.while_idle(adopt)
        state.google_sync.nudge()
        result = _state(request)
    return result.model_copy(update={"connection_changing": False})


@router.post("/resume")
def google_resume(request: Request) -> GoogleState:
    return request.app.state.google_sync.change_pause(False, lambda: _state(request))


@router.post("/tasks/sync")
def google_tasks_sync(request: Request) -> GoogleState:
    request.app.state.google_sync.sync_once()
    return _state(request)


class FollowCalendars(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_key: StrictStr = Field(pattern=r"^[0-9a-f]{32}$")
    calendar_ids: list[StrictStr]


class EventRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_key: StrictStr = Field(pattern=r"^[0-9a-f]{32}$")
    calendar_id: StrictStr
    event_id: StrictStr


def _reader(request: Request):
    client = request.app.state.google_calendar_factory()
    if client is None:
        raise NOT_CONNECTED
    check_account(request.app.state.db, client, GoogleUnavailable, request.app.state.google_auth.remember_account)
    return client


def _cache_owner(request: Request) -> str | None:
    state = request.app.state
    connected, key = state.google_auth.account_binding()
    return cache_owner(state.db, connected=connected, verified_key=key)


@router.get("/calendars")
def google_calendars(request: Request) -> list[SourceCalendar]:
    lock = request.app.state.google_sync.connection_lock
    if not lock.acquire(blocking=False):
        return []
    try:
        return list_calendars(request.app.state.db) if _cache_owner(request) else []
    finally:
        lock.release()


@router.post("/calendars/refresh")
def google_calendars_refresh(request: Request, automatic: bool = False) -> list[SourceCalendar]:
    state = request.app.state

    def refresh() -> list[SourceCalendar]:
        read_calendars(state.db, _reader(request))
        return list_calendars(state.db)

    return state.google_sync.read_from_google(refresh, automatic=automatic) or []


@router.put("/calendars")
def google_calendars_follow(body: FollowCalendars, request: Request) -> list[SourceCalendar]:
    state = request.app.state

    def follow() -> list[SourceCalendar]:
        reader = _reader(request)
        if _cache_owner(request) != body.account_key:
            raise HTTPException(409, "Your Google account changed. Refresh your calendars and review the selection again.")
        set_followed(state.db, body.calendar_ids)
        refresh_events(state.db, reader)
        return list_calendars(state.db)

    return state.google_sync.read_from_google(follow) or []


def cached_google_events(request: Request, start: str, end: str) -> list[SourceEvent]:
    lock = request.app.state.google_sync.connection_lock
    if not lock.acquire(blocking=False):
        return []
    try:
        events = list_events(request.app.state.db, start, end)
        return events if _cache_owner(request) else []
    finally:
        lock.release()


@router.get("/events")
def google_events(request: Request, start: str, end: str) -> list[SourceEvent]:
    return cached_google_events(request, start, end)


@router.post("/events/add")
def google_event_add(body: EventRef, request: Request) -> AddedEvent:
    with request.app.state.google_sync.connection_lock:
        if _cache_owner(request) != body.account_key:
            raise HTTPException(409, "Refresh your calendars with the verified Google account before adding this event.")
        return add_event_task(request.app.state.db, body.calendar_id, body.event_id)
