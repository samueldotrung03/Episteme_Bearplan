"""Connection setup routes: credentials are checked before saving and never returned."""

from __future__ import annotations

import json
import logging
import stat
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.platform import google, secrets
from backend.platform.bcourses import BCoursesUnavailable
from backend.platform.google import GoogleUnavailable, client_file, token_file
from backend.platform.secrets import read_secret, secrets_file

TOKEN = "1072~SecretTokenValue123"
REPLACEMENT = "1072~ReplacementCanary"
BCOURSES_URL = "/api/connections/bcourses"
SECRET = "GOCSPX-very-secret"
GOOGLE_URL = "/api/connections/google"
OLD_REFRESH = "test-previous-refresh"
OLD_CLIENT = "123-abc.apps.googleusercontent.com"
NEW_CLIENT = "999-new.apps.googleusercontent.com"


def _client_json(client_id=OLD_CLIENT, secret=SECRET, kind="installed"):
    return json.dumps({kind: {"client_id": client_id, "project_id": "p", "client_secret": secret,
                              "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                              "token_uri": "https://oauth2.googleapis.com/token",
                              "redirect_uris": ["http://localhost"]}}, ensure_ascii=False)


def _save_google(client, client_id=OLD_CLIENT, secret=SECRET):
    return client.put(GOOGLE_URL, json={"client_file": _client_json(client_id, secret)})


def _seed_sign_in():
    setup = json.loads(client_file().read_text())
    token_file().write_text(json.dumps({
        "refresh_token": OLD_REFRESH, "scope": " ".join(google.SCOPES),
        "authorization_key": setup.get("authorization_key"),
    }))


@pytest.fixture
def checks(client):
    seen: list[str] = []
    outcome: dict[str, object] = {"error": None}

    def checker(token):
        seen.append(token)
        if outcome["error"]:
            raise outcome["error"]
    client.app.state.bcourses_token_checker = checker
    return seen, outcome


def test_nothing_is_set_at_first(client):
    state = client.get("/api/connections").json()
    assert state["bcourses"] == {"set": False, "saved_at": None, "checked_at": None, "check_ok": None, "check_message": None}
    assert state["google"]["set"] is False and state["google"]["connected"] is False
    assert state["folder"].endswith(secrets_file().parent.name)


def test_token_is_checked_saved_owner_only_and_never_returned(client, checks, caplog):
    seen, _ = checks
    secrets_file().parent.mkdir(parents=True, exist_ok=True)
    secrets_file().write_text("# my notes\nOTHER=x\nBCOURSES_TOKEN=old\n")
    with caplog.at_level(logging.DEBUG):
        response = client.put("/api/connections/bcourses", json={"token": f"  {TOKEN}\n"})
    assert response.status_code == 200 and seen == [TOKEN]
    assert TOKEN not in response.text and TOKEN not in caplog.text
    state = response.json()["bcourses"]
    assert state["set"] and state["saved_at"] and state["check_ok"] is True
    assert read_secret("BCOURSES_TOKEN") == TOKEN and read_secret("OTHER") == "x"
    assert secrets_file().read_text().startswith("# my notes\n")
    assert stat.S_IMODE(secrets_file().stat().st_mode) == 0o600
    assert stat.S_IMODE(secrets_file().parent.stat().st_mode) == 0o700
    assert TOKEN not in client.get("/api/connections").text
    assert client.get("/api/bcourses").json()["configured"] is True


def test_rejected_token_keeps_the_old_one(client, checks):
    _, outcome = checks
    client.put("/api/connections/bcourses", json={"token": "good-token"})
    outcome["error"] = BCoursesUnavailable("bcourses_token_rejected", "no")
    response = client.put("/api/connections/bcourses", json={"token": TOKEN})
    assert response.status_code == 422 and TOKEN not in response.text
    assert response.json()["error"]["field"] == "token" and "previous token was kept" in response.json()["error"]["message"]
    assert read_secret("BCOURSES_TOKEN") == "good-token"


def test_unreachable_bcourses_saves_nothing(client, checks):
    _, outcome = checks
    old = client.put(BCOURSES_URL, json={"token": "good-token"}).json()["bcourses"]
    outcome["error"] = BCoursesUnavailable("bcourses_unreachable", "Cannot reach bCourses.")
    response = client.put("/api/connections/bcourses", json={"token": TOKEN})
    assert response.status_code == 502 and "nothing was changed" in response.json()["error"]["message"]
    assert read_secret("BCOURSES_TOKEN") == "good-token" and TOKEN not in response.text
    assert client.get("/api/connections").json()["bcourses"] == old


@pytest.mark.parametrize("token", ["two words", "", "x" * 600, "tab\there"])
def test_malformed_tokens_are_refused_without_a_check_or_echo(client, checks, token):
    seen, _ = checks
    response = client.put("/api/connections/bcourses", json={"token": token})
    assert response.status_code == 422 and seen == []
    assert (token not in response.text) if token.strip() else True
    assert read_secret("BCOURSES_TOKEN") is None


@pytest.mark.parametrize("failure", ["clear", "token", "publish"])
def test_replacement_disk_fault_has_truthful_readback_and_can_retry(client, db, checks, monkeypatch, caplog, failure):
    seen, _ = checks
    assert client.put("/api/connections/google", json={"client_file": _client_json()}).status_code == 200
    secrets_file().write_text("# keep this note\nOTHER=unrelated\n")
    old = client.put(BCOURSES_URL, json={"token": TOKEN}).json()
    status_file = secrets_file().parent / secrets.STATUS_FILENAME
    old_status = status_file.read_bytes()
    real_replace = secrets.os.replace

    def fail_replace(source, destination):
        if destination == secrets_file() and failure == "token":
            raise OSError(28, "Injected full disk")
        if destination == status_file:
            publishing = "bcourses_token" in json.loads(source.read_text())
            if failure == ("publish" if publishing else "clear"):
                raise OSError(28, "Injected full disk")
        real_replace(source, destination)

    with monkeypatch.context() as faults, caplog.at_level(logging.DEBUG):
        faults.setattr(secrets.os, "replace", fail_replace)
        failed = client.put(BCOURSES_URL, json={"token": REPLACEMENT})
        assert failed.status_code == 503
        message = failed.json()["error"]["message"]
        expected_token = REPLACEMENT if failure == "publish" else TOKEN
        assert ("new bCourses token was saved" if failure == "publish" else "token was not replaced") in message
        assert read_secret("BCOURSES_TOKEN") == expected_token
        assert seen == [TOKEN, REPLACEMENT]
        assert read_secret("OTHER") == "unrelated"
        assert not list(secrets_file().parent.glob("*.tmp"))

        # A new app instance reads the files, independent of the failed request.
        fresh = TestClient(create_app(db), base_url=str(client.base_url))
        reloaded = fresh.get("/api/connections")
        state = reloaded.json()
        assert state["google"] == old["google"]
        assert state["bcourses"]["set"] is True
        if failure == "clear":
            assert status_file.read_bytes() == old_status
            assert state["bcourses"] == old["bcourses"]
        else:
            assert all(state["bcourses"][key] is None for key in ("saved_at", "checked_at", "check_ok", "check_message"))

        # The credential on disk is the one used for provider work.
        fresh.app.state.bcourses_token_checker = seen.append
        check = fresh.post(f"{BCOURSES_URL}/check")
        assert seen[-1] == expected_token
        assert check.status_code == (503 if failure == "publish" else 200)

    for _ in range(2):
        retry = client.put(BCOURSES_URL, json={"token": REPLACEMENT})
        assert retry.status_code == 200
        assert retry.json()["bcourses"]["check_ok"] is True
        assert retry.json()["google"] == old["google"]
        assert seen[-1] == REPLACEMENT
    lines = secrets_file().read_text().splitlines()
    assert lines == ["# keep this note", "OTHER=unrelated", f"BCOURSES_TOKEN={REPLACEMENT}"]
    assert stat.S_IMODE(secrets_file().stat().st_mode) == stat.S_IMODE(status_file.stat().st_mode) == 0o600
    for credential in (TOKEN, REPLACEMENT, SECRET):
        assert all(credential not in result.text for result in (failed, reloaded, check, retry))
        assert credential not in caplog.text
        assert credential not in status_file.read_text()


@pytest.mark.parametrize("change", ["replace", "remove"])
def test_slow_token_check_cannot_publish_after_the_token_changes(client, checks, change):
    assert client.put(BCOURSES_URL, json={"token": TOKEN}).status_code == 200
    checking, release = Event(), Event()

    def checker(token):
        if token == TOKEN:
            checking.set()
            assert release.wait(5)
            raise BCoursesUnavailable("bcourses_token_rejected", "Old token rejected")

    client.app.state.bcourses_token_checker = checker
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.post, f"{BCOURSES_URL}/check")
        try:
            assert checking.wait(5)
            if change == "replace":
                changed = client.put(BCOURSES_URL, json={"token": REPLACEMENT})
            else:
                changed = client.delete(BCOURSES_URL)
            assert changed.status_code == 200
        finally:
            release.set()
        assert pending.result(timeout=5).status_code == 409
    assert client.get("/api/connections").json()["bcourses"] == changed.json()["bcourses"]


def test_check_and_remove_token(client, checks):
    _, outcome = checks
    assert client.post("/api/connections/bcourses/check").status_code == 422
    client.put("/api/connections/bcourses", json={"token": TOKEN})
    outcome["error"] = BCoursesUnavailable("bcourses_token_rejected", "no")
    state = client.post("/api/connections/bcourses/check").json()["bcourses"]
    assert state["set"] and state["check_ok"] is False and "did not accept" in state["check_message"]
    state = client.delete("/api/connections/bcourses").json()["bcourses"]
    assert state == {"set": False, "saved_at": None, "checked_at": None, "check_ok": None, "check_message": None}
    assert read_secret("BCOURSES_TOKEN") is None


@pytest.mark.parametrize("text,phrase", [
    ("not json", "not JSON"),
    pytest.param("[" * 1500 + "]" * 1500, "not a Google sign-in file", id="deeply-nested"),
    pytest.param(_client_json(secret="é" * 9000), "too large", id="oversized-multibyte"),
    (_client_json(kind="web"), "Web application"),
    (_client_json(client_id="someone-else"), "missing"),
    (_client_json(secret=" "), "missing"),
    (json.dumps({"installed": {"client_id": "a.apps.googleusercontent.com", "client_secret": SECRET,
                               "auth_uri": "https://evil.example/", "token_uri": "https://oauth2.googleapis.com/token"}}), "missing"),
])
def test_bad_google_files_keep_the_old_one(client, text, phrase):
    assert _save_google(client, secret="first").status_code == 200
    _seed_sign_in()
    response = client.put(GOOGLE_URL, json={"client_file": text})
    assert response.status_code == 422 and phrase in response.json()["error"]["message"]
    assert SECRET not in response.text
    assert json.loads(client_file().read_text())["installed"]["client_secret"] == "first"
    assert client.get("/api/google").json()["connected"]
    assert json.loads(token_file().read_text())["refresh_token"] == OLD_REFRESH


def test_google_file_saved_trimmed_owner_only_and_never_returned(client):
    response = client.put("/api/connections/google", json={"client_file": _client_json()})
    assert response.status_code == 200 and SECRET not in response.text and "123-abc" not in response.text
    assert response.json()["google"]["set"] is True and response.json()["google"]["check_ok"] is True
    stored = json.loads(client_file().read_text())
    assert set(stored["installed"]) == {"client_id", "client_secret", "auth_uri", "token_uri"}
    assert stored["authorization_key"] not in response.text
    assert stat.S_IMODE(client_file().stat().st_mode) == 0o600
    assert client.get("/api/google").json()["configured"] is True


@pytest.mark.parametrize("legacy", [True, False])
def test_same_client_preserves_sign_in_and_a_different_client_signs_out(client, revoked_tokens, legacy):
    if legacy:
        client_file().parent.mkdir(parents=True, exist_ok=True)
        client_file().write_text(_client_json())
        token_file().write_text(json.dumps({"refresh_token": OLD_REFRESH, "scope": " ".join(google.SCOPES)}))
    else:
        assert _save_google(client).status_code == 200
        _seed_sign_in()
    original = token_file().read_bytes()
    assert _save_google(client, secret="rotated").json()["google"]["connected"] is True
    assert token_file().read_bytes() == original and revoked_tokens == []
    assert _save_google(client, NEW_CLIENT).json()["google"]["connected"] is False
    assert client.get("/api/google").json()["status"] == "signed_out"
    assert not token_file().exists() and revoked_tokens == [OLD_REFRESH]


def test_removing_the_google_file_also_signs_out(client):
    assert _save_google(client).status_code == 200
    _seed_sign_in()
    state = client.delete(GOOGLE_URL).json()["google"]
    assert state["set"] is False and state["connected"] is False
    assert not client_file().exists() and not token_file().exists()


def test_other_websites_cannot_change_credentials(client, checks):
    mutations = (
        ("PUT", BCOURSES_URL, {"token": TOKEN}),
        ("POST", f"{BCOURSES_URL}/check", None),
        ("DELETE", BCOURSES_URL, None),
        ("PUT", "/api/connections/google", {"client_file": _client_json()}),
        ("DELETE", "/api/connections/google", None),
    )
    blocked = (
        ({"Origin": "https://evil.example"}, 403),
        ({"Host": "evil.example"}, 400),
    )
    for method, path, body in mutations:
        for headers, expected in blocked:
            response = client.request(method, path, json=body, headers=headers)
            assert response.status_code == expected
            assert TOKEN not in response.text and SECRET not in response.text
    assert checks[0] == [] and read_secret("BCOURSES_TOKEN") is None and not client_file().exists()


def test_status_file_holds_no_credentials(client, checks):
    client.put("/api/connections/bcourses", json={"token": TOKEN})
    client.put("/api/connections/google", json={"client_file": _client_json()})
    status = (secrets_file().parent / "status.json").read_text()
    assert TOKEN not in status and SECRET not in status and "googleusercontent" not in status


def test_real_token_check_is_one_small_read_only_request(monkeypatch):
    from backend.platform.bcourses import BCoursesClient

    class Reply:
        headers = {"Link": '<https://bcourses.berkeley.edu/api/v1/courses?page=2>; rel="next"'}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, *args):
            data, self.body = getattr(self, "body", b"[]"), b""
            return data

    seen = []
    checker = BCoursesClient(token=TOKEN)
    monkeypatch.setattr(checker._opener, "open", lambda request, timeout: (seen.append(request), Reply())[1])
    checker.check()
    assert len(seen) == 1 and seen[0].get_method() == "GET" and "per_page=1" in seen[0].full_url
    assert seen[0].full_url.startswith("https://bcourses.berkeley.edu/api/v1/courses?") and TOKEN not in seen[0].full_url


@pytest.mark.parametrize("failure", ["clear", "setup", "cleanup", "publish", "same_client_publish"])
def test_google_replacement_faults_are_truthful_and_retryable(client, db, monkeypatch, revoked_tokens, caplog, failure):
    old = _save_google(client).json()["google"]
    _seed_sign_in()
    old_setup = client_file().read_bytes()
    old_token = token_file().read_bytes()
    status_file = secrets_file().parent / secrets.STATUS_FILENAME
    real_replace = secrets.os.replace
    real_remove = google.remove_private_file
    requested = OLD_CLIENT if failure == "same_client_publish" else NEW_CLIENT
    setup_saved = failure in ("cleanup", "publish", "same_client_publish")
    still_connected = not setup_saved or requested == OLD_CLIENT

    def fail_replace(source, target):
        if target == client_file() and failure == "setup":
            raise OSError(28, "Injected full disk")
        if target == status_file:
            publishing = "google_client" in json.loads(source.read_text())
            if (publishing and failure.endswith("publish")) or (not publishing and failure == "clear"):
                raise OSError(28, "Injected full disk")
        real_replace(source, target)

    def fail_remove(path):
        if path == token_file() and failure == "cleanup":
            raise PermissionError("Injected unlink fault")
        return real_remove(path)

    with monkeypatch.context() as faults, caplog.at_level(logging.DEBUG):
        faults.setattr(secrets.os, "replace", fail_replace)
        faults.setattr(google, "remove_private_file", fail_remove)
        response = _save_google(client, requested, "synthetic-replacement-secret")
        assert response.status_code == 503
        message = response.json()["error"]["message"]
        assert ("was saved" if setup_saved else "was not replaced") in message
        assert (client_file().read_bytes() != old_setup) == setup_saved
        fresh = TestClient(create_app(db), base_url=str(client.base_url))
        readback = fresh.get("/api/connections")
        state = readback.json()["google"]
        assert state["set"] and state["connected"] == still_connected
        if failure == "clear":
            assert state == {**old, "connected": True}
        else:
            assert all(state[key] is None for key in ("saved_at", "checked_at", "check_ok", "check_message"))
        if still_connected or failure == "cleanup":
            assert token_file().read_bytes() == old_token
        else:
            assert not token_file().exists()
        if not still_connected:
            with pytest.raises(GoogleUnavailable, match="not connected"):
                fresh.app.state.google_auth.access_token()
        assert not list(secrets_file().parent.glob("*.tmp"))

    for _ in range(2):
        retry = _save_google(client, requested, "synthetic-replacement-secret")
        assert retry.status_code == 200 and retry.json()["google"]["check_ok"]
        assert retry.json()["google"]["connected"] == (requested == OLD_CLIENT)
    assert revoked_tokens == ([] if requested == OLD_CLIENT else [OLD_REFRESH])
    assert token_file().exists() == (requested == OLD_CLIENT)
    for value in (SECRET, OLD_REFRESH, OLD_CLIENT, NEW_CLIENT, "synthetic-replacement-secret"):
        assert all(value not in item.text for item in (response, readback, retry))
        assert value not in caplog.text and value not in status_file.read_text()


def test_google_replacement_leaves_setup_unchanged_if_sync_cannot_quiesce(client, monkeypatch, revoked_tokens):
    original = _save_google(client).json()["google"]
    _seed_sign_in()
    sync = client.app.state.google_sync
    while_idle = sync.while_idle
    monkeypatch.setattr(sync, "while_idle", lambda action: while_idle(action, wait_seconds=0))
    with sync._lock:
        response = _save_google(client, NEW_CLIENT)
    assert response.status_code == 502 and response.json()["error"]["code"] == "google_sync_busy"
    current = client.get("/api/connections").json()["google"]
    assert current == {**original, "connected": True}
    assert google.current_client_id() == OLD_CLIENT and revoked_tokens == []


def test_refresh_started_before_replacement_cannot_cache_old_access(client, monkeypatch):
    assert _save_google(client).status_code == 200
    _seed_sign_in()
    started, release = Event(), Event()

    def refresh(url, fields):
        started.set()
        assert release.wait(5)
        return {"access_token": "stale-access-canary", "expires_in": 3600}

    monkeypatch.setattr(google, "_post_form", refresh)
    auth = client.app.state.google_auth
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(auth.access_token)
        try:
            assert started.wait(5)
            assert _save_google(client, NEW_CLIENT).json()["google"]["connected"] is False
        finally:
            release.set()
        with pytest.raises(GoogleUnavailable, match="not connected"):
            pending.result(timeout=5)
    assert auth._access is None
