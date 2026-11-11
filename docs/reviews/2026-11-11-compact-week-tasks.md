# Compact completed Week tasks — November 11, 2026

**Pass with follow-ups.** On macOS Darwin arm64, completed current weekly leaves display the checked checkbox and muted struck-through title; metadata, drag and date controls return after reopening. Existing in-memory move forms stay mounted while hidden. The checkbox retains planned-date naming and a project/parent accessible description. Failed saves keep the row checked and show an actionable error; keyboard focus returns after save or error. Closed-week snapshots use their existing separate read-only rendering. Completing a matching active session still follows the current confirmed-time policy. No API, persistence or historical rules changed.

Reference: [completed task component in context](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=5-5292). This is a bounded current-Week row change, not the full board or Completed disclosure redesign. Completed tasks must be reopened before moving or removing their dates via this view.

Checks: `npm --prefix frontend test` (189 passed); `npm --prefix frontend run build` passed including typecheck. Guarded disposable Chrome: three responsive failure/retry/focus checks (375 dark, 640 light, 1440 dark), drag, timer eligibility and frozen-week journeys passed (7); planning journey initially failed because its restart comparison predated its newly required reopen/re-complete, then passed after updating the snapshot (1). Inspected 640 light screenshot. Fake/disposable data only; no real providers.

Manual VoiceOver, full Week redesign, Completed disclosure, planned-week Done and user acceptance remain open.
