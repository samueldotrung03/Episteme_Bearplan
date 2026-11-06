# APP-C06.1 bCourses token controls

**Pass with follow-ups.** Settings can check an existing token and distinguish
a provider rejection from an unavailable check. The latest recorded result stays
visible when an attempted check cannot be confirmed. Removal opens a native
confirmation with Keep token focused. Escape or Keep token leaves the credential
saved. Confirm removes the local token, retains selected courses, cached assignments
and imported tasks, and returns focus to setup. A failed removal stays in the
dialog and supports retry or dismissal with a status reread.

A disk error recording evidence after a successful credential write returns a
structured partial-save result. Setup clears the draft and refreshes the status
with instructions to Check saved token. Other failed saves keep the open draft.
The save/Check/Remove paths expose status only. No schema or import behavior changed.

## Verification

- macOS 26.6.2 arm64, Node 24.21.0, Chrome via Playwright, disposable data and
  fake provider outcomes. No live provider traffic.
- `npm --prefix frontend test` passed 179 tests in 16 files.
- `npm --prefix frontend run typecheck` and
  `npm --prefix frontend run build -- --outDir <temporary-directory>` passed.
- Guarded pytest used `-q -p no:cacheprovider -p tests.connections_sandbox`
  with `tests/test_settings_browser.py`, `tests/test_bcourses.py`,
  `tests/test_bcourses_browser.py`, `tests/test_connections.py`,
  `tests/test_google_controls.py` and `tests/test_google_browser.py`. It used
  `BEARPLANS_E2E_CHANNEL=chrome` and pointed `backend.platform.paths.FRONTEND_DIST`
  to the temporary build before collection. All 107 passed, including six
  Chrome journeys.
- Inspected the 640 px dark removal screenshot and verified focus, Escape,
  no horizontal overflow, failure/retry and page reload in Chrome. The API
  regression compares cached assignments, selected courses, refresh evidence
  and the same imported task before and after removal. The disk-fault case
  verifies the partial-save result and persisted credential independently.

## Open follow-ups

APP-C06.2 covers course management, assignment-review entry and work return.
Live bCourses credential verification and native/accessibility acceptance remain
pending. Browser checks of the saved-token control used simulated check responses.
