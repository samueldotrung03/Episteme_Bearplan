# APP-C05.2 — Settings credential dialogs and sign-in recovery

**Pass with follow-ups.** macOS 26.6.2 arm64, Node 24.21.0, Chrome
156.0.8078.74. This slice covers credential forms, keyboard dismissal and the
existing Google screen's sign-in handoff. It uses the existing write-only APIs
and changes no storage or provider policy.

- Settings opens a native modal for the masked bCourses token or Google Desktop
  app JSON file. Input is limited to the open form. Reopening starts empty.
  A failed save keeps the input and associates the error with its field.
  The modal blocks background interaction, guards duplicate submits, and holds
  Cancel and Escape while waiting for a write result. Dismissal before submission
  and successful save remove the draft and return focus.
- Google file selection enforces the supported extension and 16 KB limit before
  reading the file. Format and account consequences are decided by the service.
  A file save reports setup only. The Google screen reads authorization
  separately. bCourses reloads its provider view after an acknowledged save.
- Google offers an explicit link if the new tab did not open. The link is held
  in memory and shown only for the matching attempt. Leaving the view does not
  send Cancel. Explicit Cancel names the current attempt. An acknowledged
  cancellation stays visible if the status reread fails.
- Missing or unusable setup points users to Settings. Detailed provider
  status, Check/Remove and the full management flow remain later slices.

## Verification

- `npm --prefix frontend test` — 177 passed in 15 files, including mocked
  blocked-popup fallback, navigation during sign-in and cancellation with a
  failed status reread.
- `npm --prefix frontend run typecheck` — passed.
- `npm --prefix frontend run build -- --outDir "$bp_build_dir"` — passed in a
  temporary directory.
- With `backend.platform.paths.FRONTEND_DIST` set to that build and
  `BEARPLANS_E2E_CHANNEL=chrome`, pytest `-q -p no:cacheprovider
  -p tests.connections_sandbox tests/test_settings_browser.py
  tests/test_google_browser.py tests/test_connections.py
  tests/test_google_controls.py` — 86 passed, including three Chrome journeys.
  The new journey used intercepted credential responses and synthetic inputs.
  It checked focus, keyboard submit, pending Escape, failure and retry, clearing,
  and client-side file validation. Inspected the 640px Dark file error screenshot.
  The first run exposed 320px overflow from the longer button labels. After
  wrapping them, the existing 320/640/800/1440px navigation check passed.
- Full provider walkthroughs, native browser handoff, live callback and
  consent, assistive technology and actual 200% browser zoom remain open.
  No live credentials or provider requests were used.
