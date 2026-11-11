# Task capture storage and lock feedback — November 11, 2026

**Result: Pass with follow-ups.** On macOS Darwin arm64, added form-level simulated failure checks for unavailable browser recovery storage and missing Web Locks. Both retain the entered title, keep the field editable, show an alert and send no task request. Existing recovery-library tests independently exercise these fail-closed paths. This is simulated evidence, not a real browser storage or lock fault.

The first test run exposed generic feedback for a thrown storage exception. Recovery preparation now reports that storage is unavailable, no task was sent, and browser storage settings should be checked; it does not change the handling of a failure after a request has been sent. The initial full suite had 209 passing tests and one failing new assertion; after the fix `npm --prefix frontend test` passed 210 tests in 19 files, and `npm --prefix frontend run build` passed including typecheck.

A disposable local service was started and stopped, but the native Firefox control session was interrupted while its existing user window was active. No separate-window test was performed; no user browser settings were changed. Real browser storage/lock faults, separate windows, dark theme, broader accessibility and user acceptance remain open.
