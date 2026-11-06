# APP-C07.2 Google combined sync feedback

**Pass with follow-ups.** Combined sync keeps the previous full-success
timestamp until all stages finish. When a calendar stage fails, the safe
provider error identifies completed stages and preserves the provider error
code. Earlier failures keep their existing provider detail. Settings rereads
status after a failed request and avoids duplicating the same recorded error.

Plan and Projects reread after manual sync settles so they can show changes
already committed before a failure. The background version poll reads a local
baseline on mount, avoids overlapping reads, and still checks on focus and
every 30 seconds while visible. Pause, Resume and one-shot policy are unchanged.

## Verification

- macOS arm64, Node 24.21.0. `npm --prefix frontend test` passed 179 tests in
  16 files. `npm --prefix frontend run typecheck` and
  `npm --prefix frontend run build -- --outDir <temporary-directory>` passed.
- Guarded pytest ran with `-q -p no:cacheprovider -p tests.connections_sandbox`,
  `BEARPLANS_E2E_CHANNEL=chrome`, and the temporary build assigned to
  `backend.platform.paths.FRONTEND_DIST` before collection. All 141 cases
  passed across Settings/Google browser, connections, Google controls, Tasks,
  Calendar, account and calendar-reading suites.
- The fake-provider browser journey faulted selected-calendar reads after
  Tasks and publishing completed. Settings preserved the last full success and
  omitted the success receipt. Back to work showed the imported completion
  change and retained the draft. Retry preserved the pause and remote task ID
  and advanced full success. Inspected the 1440 px light partial-sync screen.
- An initial frontend run found a startup mock that counted every unknown URL
  as a task read. The fixture now handles the local version endpoint explicitly.

## Open follow-ups

Live provider checks and full native/accessibility review remain pending.
APP-C07.3 covers Plan/calendar/task integration and bCourses cross-export.
