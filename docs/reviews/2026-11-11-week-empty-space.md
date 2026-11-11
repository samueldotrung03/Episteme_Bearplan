# Compact empty Week days — November 11, 2026

**Pass with follow-ups.** On macOS Darwin arm64, reduced the weekly day-column minimum from 20rem to 6rem. Empty days no longer reserve a large blank block; columns expand for actual tasks and events and remain drop targets. Wide grid rows may still stretch shorter days to match their tallest neighbor. No records, drag behavior, completion or date rules changed. This is a scoped refinement toward the [Week design](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=6-1802), not a full board redesign.

Checks: `npm --prefix frontend run build` passed, including typecheck. Guarded disposable Chrome `tests/test_week_footer_browser.py tests/test_drag_browser.py tests/test_weekly_browser.py`: 6 passed; includes empty-day bounds, 375 dark / 640 light / 1440 dark, navigation, real drag moves/conflicts/cancellation, and planning retry. Inspected the 640 light screenshot. This CSS-only change did not rerun the unrelated frontend unit suite. No real provider or personal data used.

Compact weekly completed rows, the full Week design, manual VoiceOver and user acceptance remain open.
