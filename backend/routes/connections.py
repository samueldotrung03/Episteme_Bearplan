"""Connection setup routes: save, check and remove the bCourses token and Google sign-in file.

User request (2026-11-03): set credentials from inside the app instead of editing
files. These routes are write-only: responses say only whether a credential is set,
when it was saved and the last check result; no value or part of one is ever
returned or logged. Each credential is checked before it replaces the old one, so a
bad paste keeps the previous value. The assistant has no tool that reaches them.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from backend.domain.errors import InvalidInput
from backend.platform.bcourses import TOKEN_KEY, BCoursesClient, BCoursesUnavailable
from backend.platform import google
from backend.platform.google import GoogleClientCleanupError, GoogleSetup, client_file, parse_client_file
from backend.routes.google import disconnect_google
from backend.platform.secrets import (
    read_secret, read_status, remove_private_file, remove_secret, secrets_dir, update_status,
    write_secret,
)

router = APIRouter(prefix="/api/connections")

BCOURSES = "bcourses_token"
GOOGLE = "google_client"
TOKEN_MAX = 512
_bcourses_lock = Lock()
_google_setup_lock = Lock()


class CredentialStatus(BaseModel):
    set: bool
    saved_at: str | None = None
    checked_at: str | None = None
    check_ok: bool | None = None
    check_message: str | None = None


class GoogleClientStatus(CredentialStatus):
    setup: GoogleSetup
    connected: bool
    revoked: bool | None = None  # Result for the saved grant on removal only.


class ConnectionsState(BaseModel):
    folder: str  # Where the credentials live, with the home folder shown as ~.
    bcourses: CredentialStatus
    google: GoogleClientStatus


class TokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: StrictStr = Field(max_length=TOKEN_MAX)


class ClientFileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_file: StrictStr = Field(max_length=32 * 1024)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _status(name: str, is_set: bool) -> dict[str, object]:
    entry = read_status().get(name, {}) if is_set else {}
    keys = ("saved_at", "checked_at", "check_ok", "check_message")
    return {"set": is_set, **{key: entry.get(key) for key in keys}}


def _folder() -> str:
    folder, home = secrets_dir(), Path.home()
    try:
        return "~/" + str(folder.relative_to(home))
    except ValueError:
        return str(folder)


def _state(request: Request, revoked: bool | None = None) -> ConnectionsState:
    with _bcourses_lock:
        bcourses = CredentialStatus(**_status(BCOURSES, read_secret(TOKEN_KEY) is not None))
    with _google_setup_lock:
        auth = request.app.state.google_auth.authorization_status()
        google_status = GoogleClientStatus(
            **_status(GOOGLE, auth.setup == "configured"),
            setup=auth.setup, connected=auth.connected, revoked=revoked,
        )
    return ConnectionsState(folder=_folder(), bcourses=bcourses, google=google_status)


def _token_checker(request: Request) -> Callable[[str], None]:
    """Tests replace this; the real check is one read-only bCourses request."""
    return getattr(request.app.state, "bcourses_token_checker", None) or (lambda token: BCoursesClient(token).check())


def _check_token(request: Request, token: str) -> tuple[bool, str]:
    """(accepted, message). Only an answer from bCourses counts as a rejection."""
    try:
        _token_checker(request)(token)
    except BCoursesUnavailable as error:
        if error.code in ("bcourses_token_rejected", "bcourses_forbidden"):
            return False, "bCourses did not accept this token (it may be mistyped, expired or deleted)."
        raise BCoursesUnavailable(
            error.code, f"{error.message} The token was not checked, so nothing was changed.") from None
    return True, "bCourses accepted the token."


@router.get("")
def connections_state(request: Request) -> ConnectionsState:
    return _state(request)


@router.put("/bcourses", response_model=ConnectionsState)
def save_bcourses_token(body: TokenRequest, request: Request) -> ConnectionsState | JSONResponse:
    token = body.token.strip()
    if not token or any(ch.isspace() or not ch.isprintable() for ch in token):
        raise InvalidInput("token", "Paste the token as one piece, without spaces or line breaks.")
    accepted, message = _check_token(request, token)
    if not accepted:
        raise InvalidInput("token", f"{message} The previous token was kept.")
    with _bcourses_lock:
        # Invalidate the old check first. A stopped or failed save must never
        # associate that check with a different token.
        try:
            update_status(BCOURSES, None)
            write_secret(TOKEN_KEY, token)
        except (OSError, UnicodeError):
            raise HTTPException(
                503, "The token was not replaced. Check disk space and folder permissions, then try again."
            ) from None
        now = _now()
        try:
            update_status(BCOURSES, {"saved_at": now, "checked_at": now, "check_ok": True, "check_message": message})
        except OSError:
            return JSONResponse(
                {"error": {
                    "code": "bcourses_token_saved_check_unrecorded",
                    "message": "The new bCourses token was saved, but its check result could not be recorded. "
                    "Check disk space and folder permissions, then use Check saved token.",
                }},
                status_code=503,
            )
    return _state(request)


@router.post("/bcourses/check")
def check_bcourses_token(request: Request) -> ConnectionsState:
    with _bcourses_lock:
        token = read_secret(TOKEN_KEY)
    if token is None:
        raise InvalidInput("token", "No bCourses token is saved yet.")
    accepted, message = _check_token(request, token)
    with _bcourses_lock:
        if read_secret(TOKEN_KEY) != token:
            raise HTTPException(409, "The saved bCourses token changed during the check. Reload Settings and try again.")
        try:
            update_status(BCOURSES, {"checked_at": _now(), "check_ok": accepted, "check_message": message})
        except OSError:
            raise HTTPException(
                503, "The bCourses check result could not be recorded. Check disk space and folder permissions, then retry."
            ) from None
    return _state(request)


@router.delete("/bcourses")
def remove_bcourses_token(request: Request) -> ConnectionsState:
    with _bcourses_lock:
        try:
            update_status(BCOURSES, None)
            remove_secret(TOKEN_KEY)
        except (OSError, UnicodeError):
            raise HTTPException(
                503, "The bCourses token was not removed. Check disk space and folder permissions, then try again."
            ) from None
    return _state(request)


@router.put("/google")
def save_google_client(body: ClientFileRequest, request: Request) -> ConnectionsState:
    try:
        stored = parse_client_file(body.client_file)
    except ValueError as error:
        raise InvalidInput("client_file", f"{error} The previous sign-in file was kept.") from None

    def save() -> tuple[str | None, bool]:
        with _google_setup_lock:
            try:
                update_status(GOOGLE, None)
                refresh = request.app.state.google_auth.replace_client(stored)
            except GoogleClientCleanupError:
                raise HTTPException(
                    503, "The new Google sign-in file was saved and the previous sign-in is inactive here. "
                    "BearPlans could not remove its old token. Check folder permissions, then save the same file again."
                ) from None
            except OSError:
                raise HTTPException(
                    503, "The Google sign-in file was not replaced. Check disk space and folder permissions, then try again."
                ) from None
            now = _now()
            try:
                update_status(GOOGLE, {"saved_at": now, "checked_at": now, "check_ok": True,
                                       "check_message": "The file is a Google Desktop app sign-in file."})
            except OSError:
                return refresh, False
            return refresh, True

    sync = request.app.state.google_sync
    with sync.changing_connection():
        refresh, recorded = sync.while_idle(save)
        if refresh is not None:
            google.revoke_token(refresh)
        if not recorded:
            raise HTTPException(
                503, "The Google sign-in file was saved, but its check result could not be recorded. "
                "Check disk space and folder permissions, then save the same file again."
            )
        return _state(request)


@router.delete("/google")
def remove_google_client(request: Request) -> ConnectionsState:
    with request.app.state.google_sync.changing_connection():
        revoked = disconnect_google(request)
        with _google_setup_lock:
            try:
                update_status(GOOGLE, None)
                remove_private_file(client_file())
            except OSError:
                raise HTTPException(
                    503, "Google is signed out here, but the setup file could not be removed. "
                    "Check folder permissions, then try removing it again."
                ) from None
        return _state(request, revoked=revoked)
