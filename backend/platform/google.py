"""Google sign-in and API client (Google Tasks now; Calendar in a later step).

User decisions (2026-11-02): Desktop-app OAuth client in `google_oauth_client.json`;
the long-lived sign-in token is saved beside it in `google_token.json` (owner-only).
Both live in the secrets folder (`backend.platform.secrets.secrets_dir()`, inside the
data folder since 2026-11-03). Neither is ever logged, printed or
returned by the API. Requests go only to Google's API hosts over verified TLS,
without following redirects. Called outside any database transaction.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from backend.platform.secrets import remove_private_file, secrets_file, write_private_file

SCOPES = (
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly",
    "https://www.googleapis.com/auth/calendar.app.created",
    "https://www.googleapis.com/auth/tasks",
)
TASKS_API = "https://tasks.googleapis.com/tasks/v1"
CALENDAR_API = "https://www.googleapis.com/calendar/v3"
ALLOWED_HOSTS = ("https://tasks.googleapis.com/", "https://www.googleapis.com/", "https://oauth2.googleapis.com/")
TIMEOUT_SECONDS = 20
MAX_PAGES = 50
SIGN_IN_WAIT_SECONDS = 300
_SIGN_IN_TIMEOUT = "Google sign-in did not finish in time. Choose Connect Google to try again."
_SIGN_IN_CANCELLED = "Google sign-in was cancelled here. You can close the Google tab."
_SIGN_IN_SAVE_ERROR = (
    "The Google sign-in could not be saved. Check disk space and folder permissions, then retry."
)


@dataclass
class _SignInAttempt:
    id: str
    deadline: float


GoogleSetup = Literal["missing", "unusable", "configured"]


@dataclass(frozen=True)
class GoogleAuthorization:
    setup: GoogleSetup
    connected: bool
    verified_key: str | None
    missing_permissions: list[str]
    attempt_id: str | None
    sign_in_error: str | None


class GoogleUnavailable(RuntimeError):
    """Google could not be used; message is safe to show (never contains a token)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


NOT_CONNECTED = GoogleUnavailable("google_not_connected", "Google is not connected. Choose Connect Google first.")


def client_file() -> Path:
    return secrets_file().parent / "google_oauth_client.json"


def token_file() -> Path:
    return secrets_file().parent / "google_token.json"


def _tls_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    if not context.get_ca_certs() and Path("/etc/ssl/cert.pem").is_file():
        context = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    return context


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=_tls_context()))


def _read_json(path: Path, *, strict_io: bool = False) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None
    except OSError:
        if strict_io:
            raise
        return None
    return data if isinstance(data, dict) else None


def _oauth_client(*, strict_io: bool = False) -> dict[str, Any] | None:
    data = _read_json(client_file(), strict_io=strict_io)
    if data is None:
        return None
    try:
        info = _desktop_client(data)
    except ValueError:
        return None
    return {**info, "authorization_key": data.get("authorization_key")}


def _sign_in(info: dict[str, Any] | None) -> dict[str, Any] | None:
    data = _read_json(token_file())
    if info and data and data.get("authorization_key") == info["authorization_key"]:
        return data if isinstance(data.get("refresh_token"), str) else None
    return None


CLIENT_FILE_MAX_BYTES = 16 * 1024


def parse_client_file(text: str) -> dict[str, Any]:
    """Check a downloaded Google OAuth client file and return the part BearPlans keeps.

    Raises ValueError with a message safe to show (never containing the file's values).
    """
    try:
        size = len(text.encode("utf-8"))
    except UnicodeError:
        raise ValueError("This Google sign-in file is not valid UTF-8.") from None
    if size > CLIENT_FILE_MAX_BYTES:
        raise ValueError("This file is too large to be a Google sign-in file.")
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        raise ValueError("This is not a Google sign-in file (it is not JSON).") from None
    if not isinstance(data, dict):
        raise ValueError("This is not a Google sign-in file.")
    return {"installed": _desktop_client(data)}


def _desktop_client(data: dict[str, Any]) -> dict[str, str]:
    if "web" in data and "installed" not in data:
        raise ValueError("This sign-in file is for a Web application. In Google Cloud, create an OAuth client "
                         "of type Desktop app and download that file instead.")
    info = data.get("installed")
    if not isinstance(info, dict):
        raise ValueError("This is not a Google Desktop app sign-in file.")
    client_id, secret = info.get("client_id"), info.get("client_secret")
    auth_uri, token_uri = info.get("auth_uri"), info.get("token_uri")
    if not (isinstance(client_id, str) and client_id.endswith(".apps.googleusercontent.com")
            and isinstance(secret, str) and secret.strip()
            and isinstance(auth_uri, str) and auth_uri.startswith("https://accounts.google.com/")
            and isinstance(token_uri, str) and token_uri.startswith("https://oauth2.googleapis.com/")):
        raise ValueError("This Google sign-in file is missing its client ID, secret or Google addresses. "
                         "Download it again from Google Cloud.")
    return {"client_id": client_id, "client_secret": secret.strip(),
            "auth_uri": auth_uri, "token_uri": token_uri}


def current_client_id() -> str | None:
    info = _oauth_client()
    return info["client_id"] if info else None


class GoogleClientCleanupError(OSError):
    """The new setup was saved, but removal of an inactive local token failed."""

def _post_form(url: str, fields: dict[str, str]) -> dict[str, Any]:
    if not url.startswith(ALLOWED_HOSTS):
        raise GoogleUnavailable("google_unexpected", "Google sign-in uses an unexpected address. Nothing was changed.")
    request = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode(), method="POST")
    try:
        with _OPENER.open(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        try:
            reason = json.load(error).get("error", "")
        except (ValueError, AttributeError):
            reason = ""
        if reason in ("invalid_grant", "unauthorized_client", "invalid_client"):
            raise GoogleUnavailable(
                "google_signin_expired",
                "Google sign-in has expired or was removed. Choose Connect Google to sign in again.") from None
        raise GoogleUnavailable("google_unavailable", f"Google replied with an error (HTTP {error.code}). Try again later.") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise GoogleUnavailable("google_unreachable", "Cannot reach Google. Check your internet connection, then try again.") from None


REVOKE_URL = "https://oauth2.googleapis.com/revoke"


def revoke_token(token: str) -> bool:
    """Return whether Google acknowledged the revocation request."""
    request = urllib.request.Request(REVOKE_URL, data=urllib.parse.urlencode({"token": token}).encode(), method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with _OPENER.open(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


class GoogleAuth:
    """Holds the refresh token on disk and a short-lived access token in memory."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._access: str | None = None
        self._expires = 0.0
        self._pending: _SignInAttempt | None = None
        self._sign_in_error: str | None = None

    # ---- status

    def configured(self) -> bool:
        return _oauth_client() is not None

    def connected(self) -> bool:
        return _sign_in(_oauth_client()) is not None

    def authorization_status(self) -> GoogleAuthorization:
        """Read setup, grant and browser attempt together, without contacting Google."""
        with self._lock:
            try:
                info = _oauth_client(strict_io=True)
                setup: GoogleSetup = "configured" if info else (
                    "unusable" if client_file().exists() else "missing")
            except OSError:
                info, setup = None, "unusable"
            grant = _sign_in(info)
            scopes = set(str(grant.get("scope", "")).split()) if grant else set()
            pending = self._pending_attempt_locked()
            return GoogleAuthorization(
                setup, grant is not None, grant.get("verified_account_key") if grant else None,
                [scope.rsplit("/", 1)[-1] for scope in SCOPES if grant and scope not in scopes],
                pending.id if pending and info else None, self._sign_in_error,
            )

    def account_binding(self) -> tuple[bool, str | None]:
        with self._lock:
            data = _sign_in(_oauth_client())
            return (True, data.get("verified_account_key")) if data else (False, None)

    def remember_account(self, key: str) -> None:
        """Persist offline cache ownership on the grant verified under the provider lock."""
        with self._lock:
            data = _sign_in(_oauth_client())
            if data is None or data.get("verified_account_key") == key:
                return
            try:
                stored = {**data, "verified_account_key": key}
                write_private_file(token_file(), json.dumps(stored).encode("utf-8"))
            except OSError:
                raise GoogleUnavailable(
                    "google_account_save_failed", "BearPlans could not save the verified Google account. Check folder permissions and try again."
                ) from None

    def _pending_attempt_locked(self) -> _SignInAttempt | None:
        if self._pending and time.monotonic() >= self._pending.deadline:
            self._end_sign_in_locked(_SIGN_IN_TIMEOUT)
        return self._pending

    def _end_sign_in_locked(self, error: str | None) -> None:
        self._pending = None
        self._sign_in_error = error

    def cancel_sign_in(self, attempt_id: str) -> bool:
        with self._lock:
            pending = self._pending_attempt_locked()
            if pending is None or pending.id != attempt_id:
                return False
            self._end_sign_in_locked(_SIGN_IN_CANCELLED)
            return True

    # ---- sign-in (loopback redirect with PKCE, as Google requires for desktop apps)

    def start_sign_in(self, publish_when_idle: Callable[[Callable[[], bool]], None]) -> tuple[str, str]:
        with self._lock:
            return self._start_sign_in_locked(publish_when_idle)

    def _start_sign_in_locked(self, publish_when_idle: Callable[[Callable[[], bool]], None]) -> tuple[str, str]:
        info = _oauth_client()
        if info is None:
            raise GoogleUnavailable(
                "google_not_configured",
                "No Google sign-in file was found. Save the Desktop app credential as google_oauth_client.json in the secrets folder inside the BearPlans data folder (on a Mac, ~/Library/Application Support/BearPlans/secrets/).")
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        state = secrets.token_urlsafe(24)
        received: dict[str, list[str]] = {}
        auth = self

        class Handler(http.server.BaseHTTPRequestHandler):
            timeout = 2

            def do_GET(self) -> None:  # noqa: N802
                parsed = urllib.parse.urlsplit(self.path)
                query = urllib.parse.parse_qs(parsed.query)
                if parsed.path != "/" or query.get("state") != [state] or not ("code" in query or "error" in query):
                    self.send_error(400, "This callback did not match the Google sign-in.")
                    return
                with auth._lock:
                    accepted = auth._pending_attempt_locked() is attempt and not received
                    if accepted:
                        received.update(query)
                if not accepted:
                    self.send_error(410, "This Google sign-in is no longer waiting for a response.")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<p>Return to BearPlans to check the result. You can close this tab.</p>")

            def log_message(self, *args: Any) -> None:
                pass  # The callback URL contains the authorization code.

        class CallbackServer(http.server.ThreadingHTTPServer):
            timeout = 0.1

            def handle_error(self, request: Any, client_address: Any) -> None:
                pass  # A malformed or disconnected local request needs no traceback.

        try:
            server = CallbackServer(("127.0.0.1", 0), Handler)
        except OSError:
            raise GoogleUnavailable(
                "google_callback_unavailable",
                "BearPlans could not open its local sign-in listener. Choose Connect Google to try again.",
            ) from None
        attempt = _SignInAttempt(secrets.token_urlsafe(24), time.monotonic() + SIGN_IN_WAIT_SECONDS)
        redirect = f"http://127.0.0.1:{server.server_port}"
        url = info["auth_uri"] + "?" + urllib.parse.urlencode({
            "client_id": info["client_id"], "redirect_uri": redirect, "response_type": "code",
            "scope": " ".join(SCOPES), "state": state, "code_challenge": challenge,
            "code_challenge_method": "S256", "access_type": "offline", "prompt": "consent"})

        def wait() -> None:
            with server:
                while True:
                    with self._lock:
                        if self._pending_attempt_locked() is not attempt:
                            return
                        if received:
                            break
                    server.handle_request()
            if "error" in received or len(received.get("code", [])) != 1:
                self._finish_sign_in(attempt, error=(
                    "Google sign-in was declined or could not be authorized. Choose Connect Google to try again."
                ))
                return
            try:
                tokens = _post_form(info["token_uri"], {
                    "code": received["code"][0], "client_id": info["client_id"],
                    "client_secret": info["client_secret"], "redirect_uri": redirect,
                    "grant_type": "authorization_code", "code_verifier": verifier})
                scope = tokens.get("scope") if isinstance(tokens, dict) else None
                if not isinstance(scope, str) or not set(SCOPES).issubset(scope.split()):
                    raise GoogleUnavailable(
                        "google_missing_permissions",
                        "Google did not grant all required permissions. Choose Connect Google and allow the "
                        "requested Calendar and Tasks permissions to try again.",
                    )
                refresh, access = tokens.get("refresh_token"), tokens.get("access_token")
                if not isinstance(refresh, str) or not refresh or not isinstance(access, str) or not access:
                    raise GoogleUnavailable("google_unexpected", "Google did not return a usable sign-in. Choose Connect Google to try again.")
                expires = time.monotonic() + float(tokens.get("expires_in", 0)) - 60
            except GoogleUnavailable as error:
                self._finish_sign_in(attempt, error=error.message)
                return
            except (TypeError, ValueError, OverflowError):
                self._finish_sign_in(attempt, error="Google sent an unexpected sign-in reply. Choose Connect Google to try again.")
                return

            def publish() -> bool:
                with self._lock:
                    if self._pending_attempt_locked() is not attempt:
                        return False
                    stored = {"refresh_token": refresh, "scope": scope, "authorization_key": info["authorization_key"]}
                    try:
                        write_private_file(token_file(), json.dumps(stored).encode("utf-8"))
                    except OSError:
                        self._end_sign_in_locked(_SIGN_IN_SAVE_ERROR)
                        return False
                    self._access = access
                    self._expires = expires
                    self._end_sign_in_locked(None)
                    return True

            with self._lock:
                if self._pending_attempt_locked() is not attempt:
                    return
            try:
                publish_when_idle(publish)
            except GoogleUnavailable as error:
                self._finish_sign_in(attempt, error=error.message)

        worker = threading.Thread(target=wait, daemon=True, name="bearplans-google-signin")
        try:
            worker.start()
        except RuntimeError:
            server.server_close()
            raise GoogleUnavailable(
                "google_callback_unavailable", "BearPlans could not start Google sign-in. Choose Connect Google to try again."
            ) from None
        self._pending = attempt
        self._sign_in_error = None
        return url, attempt.id

    def _finish_sign_in(self, attempt: _SignInAttempt, *, error: str) -> None:
        with self._lock:
            if self._pending_attempt_locked() is attempt:
                self._end_sign_in_locked(error)

    def replace_client(self, stored: dict[str, Any]) -> str | None:
        """Publish setup and return an obsolete refresh token for best-effort revocation."""
        with self._lock:
            previous = _oauth_client(strict_io=True)
            data = _read_json(token_file(), strict_io=True)
            changed = previous is None or previous["client_id"] != stored["installed"]["client_id"]
            # Legacy setups and tokens both have no key. A different setup gets
            # a fresh key, so even an interrupted cleanup cannot reuse its old sign-in.
            key = secrets.token_urlsafe(24) if changed else previous["authorization_key"]
            write_private_file(client_file(), json.dumps({**stored, "authorization_key": key}, indent=2).encode("utf-8"))
            if changed:
                self._access = None
                self._expires = 0.0
                self._end_sign_in_locked(None)
            if not changed and (data is None or data.get("authorization_key") == key):
                return None
            try:
                remove_private_file(token_file())
            except OSError:
                raise GoogleClientCleanupError() from None
            refresh = data.get("refresh_token") if data else None
            return refresh if isinstance(refresh, str) else None

    def disconnect_local(self) -> str | None:
        """Remove the local sign-in and return its token for best-effort revocation."""
        with self._lock:
            data = _read_json(token_file(), strict_io=True)
            remove_private_file(token_file())
            pending = self._pending_attempt_locked()
            self._end_sign_in_locked(_SIGN_IN_CANCELLED if pending else None)
            self._access = None
            self._expires = 0.0
            refresh = data.get("refresh_token") if data else None
            return refresh if isinstance(refresh, str) else None

    # ---- access tokens

    def access_token(self) -> str:
        with self._lock:
            info = _oauth_client()
            data = _sign_in(info)
            if info is None or data is None:
                raise NOT_CONNECTED
            if self._access and time.monotonic() < self._expires:
                return self._access
        refresh = data["refresh_token"]
        tokens = _post_form(info["token_uri"], {
            "client_id": info["client_id"], "client_secret": info["client_secret"],
            "refresh_token": refresh, "grant_type": "refresh_token"})
        access = tokens.get("access_token")
        if not isinstance(access, str):
            raise GoogleUnavailable("google_unexpected", "Google sent an unexpected sign-in reply.")
        with self._lock:
            current = _oauth_client()
            if current != info or _sign_in(current) != data:
                raise NOT_CONNECTED
            self._access = access
            self._expires = time.monotonic() + float(tokens.get("expires_in", 0)) - 60
        return access

    def forget_access(self) -> None:
        with self._lock:
            self._access = None


class _GoogleApi:
    """Authorized JSON calls to Google's API hosts. Every method may raise GoogleUnavailable."""

    def __init__(self, auth: GoogleAuth) -> None:
        self._auth = auth

    def _call(self, method: str, url: str, params: dict[str, Any] | None = None,
              body: dict[str, Any] | None = None, *, retry: bool = True) -> Any:
        if not url.startswith(ALLOWED_HOSTS):
            raise GoogleUnavailable("google_unexpected", "Google sent an unexpected link. Nothing was changed.")
        full = url + ("?" + urllib.parse.urlencode(params) if params else "")
        headers = {"Authorization": f"Bearer {self._auth.access_token()}"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(full, data=data, method=method, headers=headers)
        try:
            with _OPENER.open(request, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            if error.code == 401 and retry:
                self._auth.forget_access()
                return self._call(method, url, params, body, retry=False)
            if error.code == 410:
                raise GoogleUnavailable("google_gone", "That item was already removed from Google.") from None
            if error.code == 404:
                raise GoogleUnavailable("google_not_found", "That item no longer exists in Google.") from None
            if error.code == 403:
                raise GoogleUnavailable(
                    "google_forbidden",
                    "Google refused the request. Check that the Google Calendar and Google Tasks APIs are enabled and that "
                    "BearPlans was given permission, then Connect Google again.") from None
            if error.code == 429:
                raise GoogleUnavailable("google_busy", "Google asked BearPlans to slow down. It will try again shortly.") from None
            raise GoogleUnavailable("google_unavailable", f"Google replied with an error (HTTP {error.code}). Try again later.") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise GoogleUnavailable("google_unreachable", "Cannot reach Google. Check your internet connection, then try again.") from None

    def _pages(self, url: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        token: str | None = None
        for _ in range(MAX_PAGES):
            page = self._call("GET", url, {**params, **({"pageToken": token} if token else {})}) or {}
            items += [item for item in page.get("items", []) if isinstance(item, dict)]
            token = page.get("nextPageToken")
            if not token:
                break
        return items



class GoogleTasksClient(_GoogleApi):
    """The Google Tasks calls BearPlans uses."""

    def lists(self) -> list[dict[str, Any]]:
        return self._pages(f"{TASKS_API}/users/@me/lists", {"maxResults": 100})

    def insert_list(self, title: str) -> dict[str, Any]:
        return self._call("POST", f"{TASKS_API}/users/@me/lists", body={"title": title})

    def rename_list(self, list_id: str, title: str) -> dict[str, Any]:
        return self._call("PATCH", f"{TASKS_API}/users/@me/lists/{_q(list_id)}", body={"title": title})

    def tasks(self, list_id: str) -> list[dict[str, Any]]:
        return self._pages(f"{TASKS_API}/lists/{_q(list_id)}/tasks", {
            "maxResults": 100, "showCompleted": "true", "showHidden": "true", "showDeleted": "true"})

    def insert_task(self, list_id: str, body: dict[str, Any], parent: str | None) -> dict[str, Any]:
        return self._call("POST", f"{TASKS_API}/lists/{_q(list_id)}/tasks", {"parent": parent} if parent else None, body)

    def patch_task(self, list_id: str, task_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._call("PATCH", f"{TASKS_API}/lists/{_q(list_id)}/tasks/{_q(task_id)}", body=body)

    def move_task(self, list_id: str, task_id: str, parent: str | None) -> dict[str, Any]:
        return self._call("POST", f"{TASKS_API}/lists/{_q(list_id)}/tasks/{_q(task_id)}/move", {"parent": parent} if parent else None)

    def delete_task(self, list_id: str, task_id: str) -> None:
        try:
            self._call("DELETE", f"{TASKS_API}/lists/{_q(list_id)}/tasks/{_q(task_id)}")
        except GoogleUnavailable as error:
            if error.code != "google_not_found":
                raise


class GoogleCalendarClient(_GoogleApi):
    """The Google Calendar calls BearPlans uses. Writes go only to the calendar it created."""

    def calendar_exists(self, calendar_id: str) -> bool:
        try:
            self._call("GET", f"{CALENDAR_API}/calendars/{_q(calendar_id)}")
        except GoogleUnavailable as error:
            if error.code == "google_not_found":
                return False
            raise
        return True

    def calendar_list(self) -> list[dict[str, Any]]:
        return self._pages(f"{CALENDAR_API}/users/me/calendarList", {"maxResults": 250})

    def list_events(self, calendar_id: str, time_min: str, time_max: str) -> list[dict[str, Any]]:
        """Read-only: single (expanded) events in the window, cancelled ones left out."""
        return self._pages(f"{CALENDAR_API}/calendars/{_q(calendar_id)}/events", {
            "timeMin": time_min, "timeMax": time_max, "singleEvents": "true", "orderBy": "startTime", "maxResults": 2500})

    def insert_calendar(self, summary: str) -> dict[str, Any]:
        return self._call("POST", f"{CALENDAR_API}/calendars", body={"summary": summary})

    def events(self, calendar_id: str) -> list[dict[str, Any]]:
        return self._pages(f"{CALENDAR_API}/calendars/{_q(calendar_id)}/events", {"maxResults": 2500, "showDeleted": "true"})

    def insert_event(self, calendar_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", f"{CALENDAR_API}/calendars/{_q(calendar_id)}/events", body=body)

    def patch_event(self, calendar_id: str, event_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._call("PATCH", f"{CALENDAR_API}/calendars/{_q(calendar_id)}/events/{_q(event_id)}", body=body)

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        try:
            self._call("DELETE", f"{CALENDAR_API}/calendars/{_q(calendar_id)}/events/{_q(event_id)}")
        except GoogleUnavailable as error:
            if error.code not in ("google_not_found", "google_gone"):
                raise


def _q(value: str) -> str:
    return urllib.parse.quote(value, safe="")
