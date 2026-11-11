# Today saved-focus streak

**Pass with follow-ups.** On macOS 26.6.2 arm64, added the compact streak from
the reviewed [Today design](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=5-3972).
It reuses the existing saved-session streak service, local-date rules and refresh
lifecycle. It shows current streak, today's saved minutes and accessible recent
day states; running, paused and uncertain time do not earn streak credit. The
full streak remains available in Track. A missing/invalid service response is
actionable and retryable; stale saved progress is retained when available.

The exact Figma sparkle SVG is stored locally with its original 24×24 geometry;
Vite emits it as a standalone asset. Browser assertions checked nonempty image
loading and rendered geometry. Today and streak do not add or modify backend
records. The surrounding header, Today/Week navigation, project drawer and
other design units are still pending; this is not full-screen UX parity.

## Checks

- `npm --prefix frontend test -- --run`: 184 passed. The initial run failed
  three older App fixtures that returned malformed streak data; they were
  corrected and invalid-response recovery was added and tested.
- `npm --prefix frontend run typecheck` and `npm --prefix frontend run build`
  passed; the build emitted a nonempty standalone streak SVG.
- Final built UI in installed Chrome, guarded disposable services: `tests/test_today_browser.py`
  — 4 passed in 6.90 seconds. Tested 375×900 dark, 640×900 light and 1440×900
  dark for layout, completion/reopen keyboard focus and icon geometry; a
  separate 640×800 case covered seven-task reachability and Start. Screenshots
  at all three widths were inspected; temporary evidence is in
  `/tmp/bearplans-streak-final` and may expire.
- Existing planner, timer and Settings Chrome regression on the compact-streak
  build: 15 passed in 26.78 seconds. No real provider was contacted.
- User review of this app implementation, full theme/width matrix, VoiceOver
  review for the new component and remaining redesign units remain open.
