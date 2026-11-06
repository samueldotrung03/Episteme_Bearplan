# Google Pause acknowledgement (APP-C04.3)

**Pass with follow-ups.** Pause announces a transient `pausing` state and gates
new automatic work while the current provider operation finishes. It saves
the preference only after taking the provider lock, then captures the response
under that lock. Resume uses the same serialized preference path. An overlapping
Pause or Resume returns the retryable `google_preference_busy` error through the
existing Google error envelope. A provider-lock timeout leaves the saved
preference intact. The existing Google view distinguishes Pausing from Paused.

The API tests held a full sync at the Tasks, calendar publishing and followed
calendar reading stages. Each run completed those stages once and skipped the
queued automatic sync. Tasks used the fake Tasks adapter. Publishing and reading
used instrumented stage calls to control timing. Independent calendar adapter
tests also ran. A forced zero-timeout test checked the persisted preference
and a successful retry. The UI test checked visible Pausing, disabled Sync now
and zero picker refreshes. No schema changes.

Verified on macOS 26.6.2 arm64 with disposable data and simulated providers.

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_controls.py tests/test_google_account.py tests/test_google_tasks.py tests/test_google_reading.py tests/test_google_calendar.py tests/test_connections.py
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build -- --outDir /tmp/bearplans-pause-ack.Dh13X4
git diff --check
```

133 guarded backend tests and 177 frontend tests passed. Typecheck, production
build and diff check passed. One guarded Chrome Calendar-to-Plan walkthrough
passed using the disposable build and `BEARPLANS_E2E_CHANNEL=chrome`. That
walkthrough covers the existing Calendar path. Pause timing is covered by the
API and component tests.

APP-C04.4 still owns one-shot and Resume reconciliation. The Settings controls,
live Google checks and operator acceptance remain pending.
