# APP-C06.2 bCourses course management and assignment review

**Pass with follow-ups.** Settings holds the course checklist in the bCourses
panel and links to the dedicated review view. Both surfaces share the existing
bCourses state. The review link focuses its destination heading, and Back to
work keeps the existing return behavior. The scrollable checklist keeps Refresh
and Save courses outside the scrolling area.

Opening either screen reads cached local state. The former first-visit provider
fetch now requires explicit Refresh. Save courses still writes the selection
and then refreshes assignments. If save fails, the draft stays available for
retry. If readback confirms the selection was saved before the provider fetch
failed, the interface acknowledges the saved choices and offers Refresh for
the stale assignments. Only Add creates a local task.

## Verification

- macOS 26.6.2 arm64, Node 24.21.0, Playwright with Chromium-family browser.
  Disposable data and fake provider outcomes.
- `npm --prefix frontend test` passed 179 tests in 16 files.
  `npm --prefix frontend run typecheck` and
  `npm --prefix frontend run build -- --outDir <temporary-directory>` passed.
- Guarded pytest ran with `-q -p no:cacheprovider -p tests.connections_sandbox`,
  `BEARPLANS_E2E_CHANNEL=chrome` and `backend.platform.paths.FRONTEND_DIST`
  pointing to the temporary build before collection. All 107 cases passed,
  including six browser journeys across `tests/test_settings_browser.py`,
  `tests/test_bcourses.py`, `tests/test_bcourses_browser.py`,
  `tests/test_connections.py`, `tests/test_google_controls.py` and
  `tests/test_google_browser.py`.
- The browser journey confirmed cache-only entry, scrolling to the last course
  at 640 px dark, partial-save recovery, assignment review focus, Dismiss/Restore,
  Add-once identity, explicit deadline update and task retention after deselection
  and reload. Assignment review fit at 375 px. The separate Settings navigation
  check opened course management from Track and returned to the same paused timer.
  Inspected the 640 px dark checklist screenshot.
- An initial browser run showed focus restoration overriding the explicit
  Review assignments link. The corrected build passed the heading-focus check.

## Open follow-ups

Live bCourses account verification and full native/accessibility acceptance
remain pending. Google cross-export and combined-provider behavior remain in the
Google and integrated review tickets. Next is APP-C07.1, starting with the
sharing review before Google sign-in.
