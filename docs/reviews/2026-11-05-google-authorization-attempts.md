# APP-C02.2 Google authorization attempts

November 5, 2026 · implementation review · **Pass with follow-ups**

The local Google API now separates an authorization attempt from the saved
connection. Connect returns the browser URL and a transient attempt ID. Status
exposes that ID while waiting or exchanging a code. Cancel takes the ID and
reports whether it cancelled that attempt. A stale or repeated Cancel leaves
the current attempt alone. The Settings UI can refresh status after either result.

The existing five-minute deadline now bounds acceptance of the callback and
publication of the exchanged token. The loopback listener rejects callbacks
with mismatched state and closes after the attempt ends. An incomplete request
does not hold the listener open. On denial, insufficient permissions, exchange
failure or a failed token write, status gives a retry path and preserves a
previously saved connection, including its credential file and Pause timestamp.
A successful exchange publishes the required permissions and refresh token
together. Existing stored partial grants still show missing permissions.

An invalidated attempt cannot publish credentials or errors over a newer
attempt. Cancel and discarded exchanges leave remote consent alone because
revoking a Google token can invalidate other grants to the same project.
Disconnect still tries to revoke the saved grant and reports that result.
This supersedes the late-exchange revocation wording in the historical
[Google sync review](2026-11-02-google-sync.md) and the
[build plan](../../BearPlans_Build_Plan.md).
[Google OAuth revocation documentation](https://developers.google.com/identity/protocols/oauth2/native-app#token-revoke)

## Verification

macOS 26.6.2 on arm64, Python 3.13.15, Node 24.21.0. Tests used disposable
SQLite and credential paths, real loopback HTTP and simulated Google exchanges
and revocation. The opt-in guard blocked external urllib traffic.

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox \
  tests/test_connections.py tests/test_secrets_location.py tests/test_bcourses.py \
  tests/test_google_tasks.py tests/test_google_calendar.py tests/test_google_reading.py \
  tests/test_google_controls.py tests/test_google_account.py
npm --prefix frontend test
npm --prefix frontend run typecheck
bp_build_dir=$(mktemp -d /tmp/bearplans-settings-build.XXXXXX)
npm --prefix frontend run build -- --outDir "$bp_build_dir"
git diff --check
```

- Backend 124 passed. API-05 covered denial, missing scopes, exchange failure,
  malformed data, token-save failure and the fake-clock deadline during waiting
  and exchange. API-06 held a fake exchange open through Cancel, retry, deadline,
  Disconnect, file removal and client change. Both stale success and stale error
  were exercised. A successful retry was readable from a fresh auth object and
  its file had mode 0600.
- API-09 covered hostile Host and Origin on Cancel and checked provider and
  storage canaries in responses and logs. The broader suite also ran the
  existing local request, credential and account regressions.
- Frontend 166 passed across 15 files. Type checking and the disposable production
  build passed. Vite noted that its temporary output directory is outside the
  project and would not be emptied.
- Git whitespace and relative links in this review passed.

## Handoff

Wire the Cancel control and status in APP-C07.1. Dismissing the status dialog
should leave the attempt active. UI-05 and LIVE-02 still need the Settings
walkthrough and actual provider/browser evidence. This review used no system
browser, live provider, real credentials or user database. A fresh auth object
check covers persisted success, while an actual app restart remains a separate
gate. APP-C02.3 is next for Disconnect coordination with sync and reads, and
for the distinction between local removal and confirmed remote revocation.
