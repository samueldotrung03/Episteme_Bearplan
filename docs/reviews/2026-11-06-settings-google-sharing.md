# APP-C07.1 Google sharing review before sign-in

**Pass with follow-ups.** Connect and Reconnect open a review before creating
an OAuth attempt. It covers selected calendar reads, publishing timed plans to
the BearPlans calendar, and syncing all local projects and tasks, including
bCourses assignments added as tasks. The review explains that calendar selection
affects reads only, identifies task fields shared, and distinguishes personal
Google lists from lists created by BearPlans.

Cancel and Escape dismiss the review without an authorization request. Continue
uses the existing browser flow, fallback link and attempt-specific cancellation.
An unavailable status disables new sign-in until status can be read. No backend,
credential storage or sync behavior changed.

## Verification

- macOS 26.6.2 arm64, Node 24.21.0. Disposable data, fake clients and synthetic
  browser authorization responses.
- `npm --prefix frontend test` passed 179 tests in 16 files.
  `npm --prefix frontend run typecheck` and
  `npm --prefix frontend run build -- --outDir <temporary-directory>` passed.
- Guarded pytest ran with `-q -p no:cacheprovider -p tests.connections_sandbox`,
  `BEARPLANS_E2E_CHANNEL=chrome` and `backend.platform.paths.FRONTEND_DIST`
  pointed to the temporary build before collection. All 89 cases passed across
  `tests/test_settings_browser.py`, `tests/test_google_browser.py`,
  `tests/test_connections.py` and `tests/test_google_controls.py`.
- Browser verification entered from Settings, checked the review copy and focus
  at 640 px dark, dismissed via Escape with zero requests, and entered the same
  review through missing-permissions Reconnect. Continue made one request and
  showed the fallback link. The unit test exercised navigation while pending
  and attempt-specific Cancel when a subsequent status read failed.
- The first unit run exposed missing native dialog methods in jsdom. The
  corrected fixture passed, and actual focus and Escape used native browser
  behavior in the browser test.

## Open follow-ups

Live consent, browser callback, and full native/accessibility acceptance remain
pending. APP-C07.2 next reconciles combined sync feedback and work-view refresh.
