# Compact active Week task details — November 11, 2026

**Result: Pass with follow-ups.** Active Week cards group planned start time, deadline and estimate into a wrapping row inspired by the [Week reference](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=6-1802). Existing date, timer, move, completion and error behavior remains; historical cards and saved data are unchanged. This is a small layout step, not full Figma parity.

## Verification

On macOS Darwin arm64:

- `npm --prefix frontend test`: 191 passed.
- `npm --prefix frontend run build`: passed, including TypeScript checking.
- `BEARPLANS_E2E_CHANNEL=chrome BEARPLANS_EVIDENCE_DIR=/tmp/bearplans-week-details .venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_compact_week_tasks_browser.py tests/test_drag_browser.py tests/test_timer_eligibility_browser.py tests/test_google_browser.py`: 12 passed. Reopen and retry tests cover 375 dark, 640 light and 1440 dark, with due/estimate alignment at 640 and no horizontal overflow.
- Inspected the 640 light reopened-task screenshot. User acceptance and VoiceOver remain untested; broader Week and project redesign remain open.
