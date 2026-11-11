# Task capture cross-tab focus — November 11, 2026

**Result: Pass with follow-ups.** On macOS Darwin arm64, used two in-app browser
tabs and a disposable schema-24 service. Stopped the service before submitting
a synthetic task in the first tab, restarted it, and checked the pending save in
the second. The first tab showed the resolved-elsewhere message and focused
Cancel. Enter closed its form and refreshed the list with the single task. The
test used tabs, not separate windows; both tabs were closed and service stopped.

That browser check exposed focus falling to the page after closing the stale
form, because Add task is disabled during refresh. The form now returns focus to
the project heading instead, including during a failed refresh. An App test checks
the successful refresh and heading focus. This final adjustment has not yet been
tested initially in simulation. A subsequent in-app browser recheck repeated the
two-tab outage and recovery: after Enter closed the stale form, focus landed on
the Inbox heading, Tab reached Add task, and the refreshed list showed the single
synthetic task. Both tabs were closed and the disposable service stopped. A screen
reader and separate windows were not tested.

`npm --prefix frontend test` passed 213 tests in 19 files and `npm --prefix
frontend run build` passed including typecheck. Real browser storage/lock faults,
broader theme coverage, separate-window focus and user acceptance remain open.
