# Google automatic sync while paused (APP-C04.2)

**Pass with follow-ups.** The Calendar view marks its empty-cache refresh as
automatic and aborts the client request when its effect is superseded. The API
checks durable Pause inside the provider lock, before account verification or
provider activity. A suppressed automatic refresh returns an empty list. The
explicit Refresh calendars action uses the existing route without the automatic
flag and preserves the saved Pause. The cache reads continue to use the current
account guard. No persistence or default changes.

| Trigger | Evidence |
| --- | --- |
| Periodic service sync | A fresh app and database handle observe an automatic attempt after a paused restart. No fake Tasks calls or last-attempt write. |
| Debounced local edit | An API task save survives, wakes the worker and records no sync attempt or provider calls. |
| Startup and OAuth publication | Source inspection found no separate startup sync. The service starts the same worker; authorization publishes the grant and increments the change version without running a separate sync. Explicit sign-in still verifies identity. |
| Tasks push/pull, calendar publish and followed-calendar reads | Full sync checks Pause before creating a provider client or entering the shared sync function that runs these operations. |
| Empty-cache refresh on view open | UI tests distinguish automatic and deliberate requests. A queued automatic request sees Pause set while waiting for the lock and performs zero calendar-list calls. An explicit refresh afterward reads calendars and keeps Pause. |
| View focus and Plan reads | Source inspection confirmed that the browser poll reads the local change counter and Plan uses account-scoped cached events. |

Verified on macOS 26.6.2 arm64 with disposable databases and simulated providers.
The targeted Chrome walkthrough used a fresh production build and exercised
Calendar setup through Plan. The queued Pause race is covered by the API test
with a deterministic lock boundary.

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_controls.py tests/test_google_account.py tests/test_google_tasks.py tests/test_google_reading.py tests/test_connections.py
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build -- --outDir /tmp/bearplans-pause-build.4GKem3
git diff --check
```

114 guarded backend tests and 176 frontend tests passed. Typecheck, production
build and diff check passed. One guarded Chrome test passed from
`tests/test_google_browser.py`, using `BEARPLANS_E2E_CHANNEL=chrome` and pointing
`backend.platform.paths.FRONTEND_DIST` at the disposable build.

APP-C04.3 owns Pause acknowledgement while in-flight operations drain and
coordination with simultaneous Resume. APP-C04.4 owns full one-shot/Resume
reconciliation. Service process lifecycle and live provider acceptance remain
pending.
