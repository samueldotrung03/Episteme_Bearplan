# Task capture resolved-elsewhere focus — November 11, 2026

**Result: Pass with follow-ups.** When a pending save is resolved in another
window, its status button disappears. If focus was inside that form, the form now
moves focus to Cancel so the user can close it and refresh the task list. If focus
was elsewhere, the form leaves it there. The existing simulated cross-window App
test checks the first path and a form test checks the second.

On macOS Darwin arm64, `npm --prefix frontend test` passed 213 tests in 19 files
and `npm --prefix frontend run build` passed including typecheck. This new focus
behavior has not been checked in two real browser windows or with a screen reader.
Chrome was unavailable to the browser-control session for the planned dark-theme
matrix; the disposable in-app browser tab and service were closed. G-01, G-02 and
user acceptance remain open.
