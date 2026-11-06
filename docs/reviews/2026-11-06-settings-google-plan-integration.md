# APP-C07.3 — Google Plan and task integration review

**Pass with follow-ups** on macOS 26.6.2 arm64, using installed Chrome,
fake Google and bCourses clients, and disposable SQLite data.

- The previous Google adapter completed open children when a parent was
  checked in Google. This conflicted with the shared completion rule. The
  adapter now accepts incoming completion changes only on leaves and writes
  the derived parent state back to its mapped Google task. Checked and
  unchecked parent cases and a valid child tick passed. Previously saved
  completion records stay as stored because the source of those changes is
  not recoverable from the current task records.
- Chrome showed that saving an empty calendar selection clears the source
  events from Plan while retaining the added task and its placement. The
  Settings copy now explains that calendar selection controls reads, that
  added tasks remain, and that all-task sync has a separate scope.
- The bCourses and Google Tasks integration regression verifies that course
  refresh alone exports no assignments. Explicit Add and repeated Add keep
  one local task and one Google task per source, including an undated
  assignment. Keep mine retains the deadline in both systems. Use new due
  date updates the mapped task in place. Unfollowing the course keeps both
  tasks in the export.
- The guarded suite also covered event Add identity, untimed placements,
  publishing with a 30-minute reminder, retiming without duplication, past
  event retention, start-time carryover, and frozen closed-week history.

## Commands and results

- `npm --prefix frontend test` — 179 passed in 16 files.
- `npm --prefix frontend run typecheck` — passed.
- `npm --prefix frontend run build -- --outDir /tmp/bearplans-c073.nBvzUs` — passed.
- `pytest.main` from `.venv/bin/python`, with
  `backend.platform.paths.FRONTEND_DIST` set to that build, Chrome selected by
  `BEARPLANS_E2E_CHANNEL=chrome` and arguments `-q -p no:cacheprovider -p tests.connections_sandbox`.
  Test modules under `tests/`: `test_settings_browser.py`,
  `test_google_browser.py`, `test_connections.py`, `test_google_controls.py`,
  `test_google_tasks.py`, `test_google_calendar.py`, `test_google_account.py`,
  `test_google_reading.py`, `test_bcourses.py`, `test_bcourses_browser.py`,
  and `test_weeks.py` — 245 passed.
- Scoped diff and review links checked.

C07.4 covers reconnect and disconnect recovery. C08 owns the full integrated
regression and accessibility pass, including broader source-event change and
recurrence coverage. Real-account behavior awaits separately authorized
operator evidence.
