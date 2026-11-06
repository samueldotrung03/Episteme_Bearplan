# APP-C02.1 — bCourses credential replacement recovery

**Pass with follow-ups.** This review covers the bCourses part of APP-C02.1
under the November 5 “continue” request. Google client replacement, OAuth, sync
coordination and the Settings UI have their own pending work. The baseline and
scope are recorded in [APP-C01](2026-11-05-settings-application-baseline.md)
and the [execution plan](../../frontend/plans/settings-connections/EXECUTION_PLAN.md#app-c02--credentialauth-replacement-cancellation-and-account-boundaries).

## Behavior

The route checks the proposed token through the existing bounded, read-only
provider request. A rejected or unreachable check leaves both files as they
were. After acceptance, the route clears the old bCourses check result,
replaces the token in the private env file, then records the new result.
Each file replacement is atomic. The bCourses routes serialize the local
transition, including removal, and a check in flight can publish only for the
token it checked. Unrelated env lines and Google status are preserved. The
credential remains outside SQLite. There are no new product defaults.

| Local outcome | Saved token | Readback and recovery |
| --- | --- | --- |
| Clearing old check fails | Previous | Previous record remains. Fix disk space or folder permissions and retry. |
| Old check cleared and token write fails | Previous | Token remains usable. The check status is unknown until a new check or save succeeds. |
| Token saved and result write fails | Replacement | Token is set with unknown check status. The response explicitly says the replacement was saved and offers Check and save again. |
| Retry succeeds | Replacement | The provider checks the token again and one token line and one current check record remain. |

A failed local write returns a structured 503 without exception details.
An old check that returns after removal or replacement with a different token
returns a 409 before it can publish stale results. Failed atomic writes attempt
to remove their temporary file. This contract covers the single local service
and its own routes. Direct file edits and receipts written by earlier builds
are outside the transition lock.

## Verification

macOS 26.6.2 arm64, Python 3.13.15, Node 24.21.0. Base commit `83fdbfe`,
with the uncommitted APP-C01 fixture and separate concurrent Google account
patch. The tests used fake providers and disposable data, including a loopback
callback in the existing Google controls suite.

- **API-02/04/09:** disk faults at the atomic replace boundary before
  invalidation, before token replacement and before publication. Checked durable
  readback, the actual credential supplied to the next fake provider check,
  repeated retry, permissions and cleanup. The rejected/offline and malformed
  cases, stale in-flight check races, and Origin/Host guards passed.
- **DATA-02/03:** a disposable subprocess probe used TestClient with a fake
  token checker and denied stdlib HTTP. Injected `os._exit(86)` immediately
  after clearing the result, and separately after publishing the token file.
  In each case a fresh process saw the expected old/new token with unknown check
  status and saved the replacement successfully. A SQLite backup and restore
  preserved the same synthetic task, contained neither token canary and
  restored no secrets folder. The route tests also checked canaries in HTTP
  responses, status JSON and captured logs.
- Frontend regression: `npm --prefix frontend test` (166 in 15 files),
  `npm --prefix frontend run typecheck`, and
  `npm --prefix frontend run build -- --outDir "$bp_build_dir"` with an empty
  disposable directory passed.

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox \
  tests/test_connections.py tests/test_secrets_location.py tests/test_bcourses.py \
  tests/test_google_tasks.py tests/test_google_calendar.py tests/test_google_reading.py \
  tests/test_google_controls.py tests/test_google_account.py
```

101 tests passed. An initial expanded guard check expected HTTP 403 for both
headers. The test now asserts the existing contract of 400 for a non-loopback
Host and 403 for a foreign Origin. `test_google_account.py` belongs to the
concurrent working tree. The process probe exercised file publication and reload through ASGI.
Hardware power loss, the production launcher, browser Settings and live bCourses
were outside this verification. The existing Google sync nudge on successful
API mutations remains part of the later trigger review.
