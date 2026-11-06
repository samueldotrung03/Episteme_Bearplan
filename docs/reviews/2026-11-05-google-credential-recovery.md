# APP-C02.1 — Google sign-in file replacement recovery

**Pass with follow-ups.** Completed the Google half of APP-C02.1 under the
November 5 “continue” request. The [bCourses review](2026-11-05-bcourses-credential-recovery.md)
covers the other half. See the [execution plan](../../frontend/plans/settings-connections/EXECUTION_PLAN.md#app-c02--credentialauth-replacement-cancellation-and-account-boundaries).

## Behavior and fault boundaries

The upload validates the Desktop-app file locally. It checks the existing sync
barrier before changing anything. If the wait times out, the API returns
`google_sync_busy` and the upload leaves the previous setup and sign-in intact.
An automatic run queued behind the upload rechecks the connection under the same
lock.

The client file and refresh token share a private BearPlans authorization key.
Legacy pairs still work. The server generates a fresh key for a different OAuth
client. A same-client replacement keeps its key and existing sign-in. A
different-client replacement makes the old token unusable at the moment the
new client file is published. The app invalidates any pending sign-in for the
old client and rejects an old refresh result if the saved setup or sign-in
changed while it was in flight.

| Outcome | Setup and local sign-in | Recovery |
| --- | --- | --- |
| Invalid file or sync still busy | Prior setup, sign-in and receipt | Correct the file or wait for sync, then retry. |
| Clearing receipt or writing setup fails | Prior setup and sign-in. Receipt is absent if it was already cleared. | Fix disk space or permissions and retry. |
| New setup saved but old token removal fails | New setup, signed out. Any old token file is inactive. | Save the same file again to retry cleanup. |
| New setup saved but receipt write fails | New setup. Same-client sign-in is retained. Different-client setup is signed out. | Save the same file again to record the file check. |
| Different-client save succeeds | New setup, signed out. The obsolete local token is removed. | Connect Google when ready. |

Remote revocation of the obsolete token remains best effort. The replacement
result describes local authorization and does not certify Google's revocation.
Local tasks, Pause, sync history and account mappings stay in the existing
database. File validation supplies no evidence of OAuth consent, Google API
access or current permissions.

## Verification

macOS 26.6.2 arm64, Python 3.13.15 and Node 24.21.0. Base commit `83fdbfe`
with the local APP-C01 and bCourses patches and the concurrent Google account
patch. Existing tests supplied fake provider adapters and an isolated
loopback callback. No live provider request or real data folder was used.

- **API-03/04/09:** invalid JSON, nested and multibyte oversized input, Web
  client, unapproved host and missing fields. Existing sign-in survives invalid
  files. Injected faults clearing the receipt, publishing the client file,
  unlinking the old token and writing the new receipt. Checked the same-client
  and different-client outcomes, repeated retries, readback in a fresh app,
  token permissions, temporary cleanup and absence of credential values in
  API results, captured logs and status JSON. Verified existing Host and Origin
  protections.
- **API-06/07, scoped replacement:** fake callback exchange released after
  the client changed could not publish an old sign-in. A fresh callback under
  the new client survived reload. A delayed token refresh could not restore old
  cached access. Held the sync lock through a zero-wait timeout and verified
  no upload mutation. Verified that disconnected automatic sync skips work.
- **DATA-02/03:** ran a disposable ASGI subprocess probe with
  `PYTHONPATH=. .venv/bin/python "$bp_probe/probe.py" "$bp_probe"`. It exited
  immediately after clearing the receipt and, in a separate run, after
  publishing the new client file before old-token cleanup. A fresh process
  read the correct authorization state and retried safely. SQLite backup
  and restore preserved the same sample task and Pause timestamp and contained
  no fixture credentials or secrets folder.

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox \
  tests/test_connections.py tests/test_secrets_location.py tests/test_bcourses.py \
  tests/test_google_tasks.py tests/test_google_calendar.py tests/test_google_reading.py \
  tests/test_google_controls.py tests/test_google_account.py
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build -- --outDir "$bp_build_dir"
git diff --check
```

Final results were 112 backend tests, 166 frontend tests, typecheck and the
production build into a disposable directory. The initial expanded backend
run had three fixture assertion failures. The deeply nested input can be parsed
then rejected as the wrong shape, the multibyte fixture needed real UTF-8
instead of JSON escapes, and the expected receipt needed to include the
fixture's newly seeded connection. All passed after correcting the fixtures.

APP-C02.2 still covers the complete authorization attempt lifecycle, including
missing permissions, denial, explicit cancellation and timeout with a prior
sign-in. APP-C02.3 and APP-C02.4 cover broader Disconnect coordination, direct calendar
read races and account identity. The sync timeout guard also applies to other
callers of `while_idle`. Pause still writes its preference before waiting,
so a timeout can coexist with a persisted Pause. The acknowledgement and
all-trigger review stays in APP-C04. The production launcher, browser Settings,
hardware power loss and live consent are separate checks.
