# APP-C05.3 — Settings provider panels and Google sync controls

**Pass with follow-ups.** Verified on macOS 26.6.2 arm64, Node 24.21.0 and
Chrome 156.0.8078.74. This slice covers the Settings summaries and backed
controls from UI-01 and UI-06, with the existing Google calendar journey as a
UI-08 regression. Course management and account/disconnect review remain
separately scoped.

- bCourses shows saved token/check evidence separately from assignment refresh.
  Google shows file setup, authorization, operation, automatic sync preference
  and last full sync separately. Failed reads retain previous results and
  expose retry. Opening Settings reads local status without starting provider
  sync. Google status refreshes every three seconds while Settings is open.
- Pause, Resume and Sync once call the existing API. Pausing appears during
  the request and Paused depends on acknowledged service state. Pending actions
  block duplicate submissions. On failure, the last known preference and
  success remain visible. Sync once keeps Pause and a successful sync refreshes
  Plan and project tasks. No backend or storage change was needed.
- The existing provider screens remain reachable. bCourses Check/Remove and
  course selection belong to APP-C06. Google scope review, calendar selection
  and account/disconnect recovery belong to APP-C07.

## Checks

- `npm --prefix frontend test` — 179 passed in 16 files. New cases exercise
  deferred Pause acknowledgement, offline Sync once and retry, Resume and
  independent status-read recovery.
- `npm --prefix frontend run typecheck` and
  `npm --prefix frontend run build -- --outDir "$bp_build_dir"` — passed.
- With `backend.platform.paths.FRONTEND_DIST` set to the disposable build and
  `BEARPLANS_E2E_CHANNEL=chrome`, pytest `-q -p no:cacheprovider
  -p tests.connections_sandbox tests/test_settings_browser.py
  tests/test_google_browser.py tests/test_connections.py
  tests/test_google_controls.py` — 87 passed, including four Chrome journeys.
  The new journey used a disposable database and fake Google clients, checked
  the saved Pause through page reload, compared the persisted timestamp after
  Sync once and verified Resume clears it. Inspected the 640px Dark capture.
  Existing Settings width, work-context, dialog and calendar journeys passed.
- Live providers, native browser handoff, service-restart walkthrough, actual
  200% browser zoom and assistive technology remain open. No real provider
  credentials or external requests were used.
