# APP-C07.4 — Google reconnect and disconnect recovery

**Pass with follow-ups** on macOS 26.6.2 arm64. Chrome ran with fake
providers and disposable data.

- Settings directs blocked connections to Open Google. Reconnect remains
  available through the existing sharing review. A verified account mismatch
  or unowned set of links offers a separate review using the backend's
  review key. Confirmation rechecks that account on the server. The review
  explains which links and calendar selections are cleared locally, what
  stays in the old account, and what the next sync can export.
- Chrome at 640 × 800 confirmed that a mismatch blocks writes, Escape
  cancels review and returns focus, and confirming while paused sends no
  writes until Sync once. The local task was exported once to the newly
  accepted account and the original account's resources were preserved.
- Disconnect now reviews the removal of local sign-in and the separate
  revocation attempt. Cancel returned focus and did not call revocation.
  With fake revocation unavailable, the local sign-in was removed, Pause
  and the setup file stayed, and the receipt explicitly reported that
  revocation was unconfirmed. Local tasks and the exported copy survived.
- The setup dialog explains that replacing the Desktop app identity
  requires signing in again. Existing API tests covered credential failures,
  same-account reconnect and reuse, account-cache isolation, stale review,
  and disconnect coordination with active work.

## Commands and results

- `npm --prefix frontend test` — 178 passed in 16 files. The former
  mocked disconnect receipt case moved to the Chrome walkthrough.
- `npm --prefix frontend run typecheck` — passed.
- `npm --prefix frontend run build -- --outDir /tmp/bearplans-c074.niMFoY` — passed.
- `pytest.main` via `.venv/bin/python` with `backend.platform.paths.FRONTEND_DIST`
  set to that build, `BEARPLANS_E2E_CHANNEL=chrome` and flags
  `-q -p no:cacheprovider -p tests.connections_sandbox`. Test modules under
  `tests/` were `test_google_browser.py`, `test_settings_browser.py`,
  `test_google_account.py`, `test_google_controls.py`, `test_connections.py`,
  `test_google_tasks.py`, `test_google_calendar.py`, `test_google_reading.py`,
  `test_bcourses.py` and `test_bcourses_browser.py` — 162 passed.
- The first browser run counted the fixture's unrelated personal Google task
  as an export. The corrected assertion matches the live exported task by
  title and still fails on duplicates. The complete guarded suite passed on
  rerun.
- Scoped diff and documentation links checked.

APP-C08 covers broader process, fault, layout and accessibility evidence.
Live provider access and operator acceptance remain open.
