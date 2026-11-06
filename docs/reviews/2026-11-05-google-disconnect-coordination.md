# APP-C02.3 Google Disconnect coordination

November 5, 2026 · implementation review · **Pass with follow-ups**

Disconnect, setup removal and setup replacement now wait for active Google
task sync or calendar reads before changing credentials. A change blocks new
provider work and invalidates already queued requests for the previous
connection. A timeout returns a retryable busy error before credential changes.
New browser sign-in waits through cleanup and revocation. Cached calendar reads
continue locally, and a rejected follow request leaves the existing calendar
selection and cache intact.

Disconnect cancels pending authorization after removing the local token. It
keeps the setup file, local work, cached events and the Pause setting. Removing
setup also removes its file and check receipt. If the token cannot be removed,
the current sign-in is kept and revocation is skipped. If setup cleanup fails
after the sign-out, the response reports the partial result and offers a retry.

Disconnect and setup removal distinguish an acknowledged revocation, an
unconfirmed result and the absence of a saved grant. Only HTTP 200 from the
revocation endpoint counts as acknowledgement. The operation still succeeds
locally if Google declines the request or is unavailable. No deletion request
for remote tasks or calendar events is part of either operation.
[Google OAuth documentation](https://developers.google.com/identity/protocols/oauth2/native-app#token-revoke)

## Verification

macOS 26.6.2 on arm64, Python 3.13.15, Node 24.21.0. Tests used disposable
SQLite and credential paths and simulated Google responses. The connection
fixture blocked external urllib traffic.

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox \
  tests/test_connections.py tests/test_secrets_location.py tests/test_bcourses.py \
  tests/test_google_tasks.py tests/test_google_calendar.py tests/test_google_reading.py \
  tests/test_google_controls.py tests/test_google_account.py
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox \
  tests/test_google_controls.py -k 'drains_active or queued_under or cannot_start_during'
npm --prefix frontend test
npm --prefix frontend run typecheck
bp_build_dir=$(mktemp -d /tmp/bearplans-settings-build.XXXXXX)
npm --prefix frontend run build -- --outDir "$bp_build_dir"
git diff --check
```

- 138 guarded backend checks passed. API-07 covered Disconnect during active
  sync and calendar refresh, old queued reads and manual/automatic sync, Connect
  during revocation, repeated Disconnect, offline revocation, and removal retries
  after busy, token, receipt and setup file failures. Retained cached events, task
  identity, Pause and signed-out state in a fresh auth object were checked.
- All six race cases passed on two additional runs. An earlier focused run had
  four test fixture failures. The sync stub counted two legitimate list calls as
  separate syncs, and the revocation transport check initially called the
  autouse mock. The final run corrected both fixtures.
- API-09 covered hostile Host and Origin on Disconnect and the existing setup
  route protections. Injected failure text and synthetic credential values
  stayed out of error responses.
- Frontend 166 passed across 15 files. Type checking, the disposable production
  build, Git whitespace and local review links passed.

## Handoff

APP-C02.4 is next. Review account verification before reusing mappings and how
a successful browser reconnect can interact with an active operation. Account
adoption and cache isolation remain separate from this teardown check. Settings
recovery and revocation copy are scoped to APP-C07.4. Browser, live provider
and service restart acceptance remain open.
