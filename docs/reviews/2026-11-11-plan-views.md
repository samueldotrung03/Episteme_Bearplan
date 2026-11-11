# Today, Week and Projects navigation — 2026-11-11

**Pass with follow-ups.** The Plan screen opens on Today and offers separate Today, Week and Projects controls, informed by [Today](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=5-3972) and [Week](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=6-1802). The existing project editor and week board remain mounted when hidden, retaining drafts, viewed week, and selected day. Settings returns to the same Plan view. A planning read failure can be retried from Today. This change does not write records or change timer, planning, connection or completion rules.

On macOS Darwin arm64, `npm --prefix frontend run build` passed including typecheck, and `npm --prefix frontend test -- --run` passed 185 tests. Disposable Chrome runs used `-q -p no:cacheprovider -p tests.connections_sandbox`, `BEARPLANS_E2E_CHANNEL=chrome` and a temporary evidence directory:

- `tests/test_today_browser.py tests/test_settings_browser.py`: 19 passed, including keyboard switching, draft and week retention, Settings and timer return, 375 dark / 640 light / 1440 dark view checks and other Settings widths. Week at 640 light was visually inspected.
- `tests/test_weeks_browser.py tests/test_drag_browser.py`: 3 passed; `tests/test_weekly_browser.py`: 1 passed.
- `tests/test_m1_journey_browser.py tests/test_timer_browser.py`: 3 passed; the two project browser cases in `tests/test_e2e_browser.py` passed in the preceding run.
- `tests/test_bcourses_browser.py tests/test_google_browser.py tests/test_assistant_browser.py tests/test_timer_eligibility_browser.py`: 9 passed with simulated providers.

Initial browser and frontend runs failed because older tests assumed Projects and Week were simultaneously visible; tests now select the relevant view. An initial new browser assertion read the previous week before navigation finished; it now waits for the changed heading. Integration checks use disposable data and do not establish live provider acceptance. The existing Week and Projects content is still the previous presentation, not the completed prototype: project drawer/task forms, weekly visual refinements, Earlier unfinished, planned-week Done and ordering remain outstanding. The full redesign and user acceptance remain open.
