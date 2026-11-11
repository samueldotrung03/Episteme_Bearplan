# Week day counts — November 11, 2026

**Result: Pass with follow-ups.** The compact Week selector shows the number of planned task placements for each day, including completed tasks. Its full accessible button names include date, Today when applicable, and a singular/plural task count. Closed weeks use frozen placements and snapshot tasks; calendar events are not included. No data or planning rules changed. Reference: [Week prototype](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=6-1802).

## Verification

On macOS Darwin arm64:

- `npm --prefix frontend test`: 191 passed. An initial run exposed a concatenated accessible name; the name was corrected and all tests passed on rerun.
- `npm --prefix frontend run build`: passed, including TypeScript checking.
- `BEARPLANS_E2E_CHANNEL=chrome BEARPLANS_EVIDENCE_DIR=/tmp/bearplans-day-count-final .venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_drag_browser.py tests/test_week_footer_browser.py tests/test_weeks_browser.py`: 6 passed. Checks cover moving a task and updated counts, selected day, cancellation, closure and responsive layouts at 375 dark, 640 light and 1440 dark.
- Inspected the 375 dark screenshot; user acceptance and VoiceOver remain untested. Wide Week uses day columns and does not show this compact selector. Further Week and Projects design work remains.
