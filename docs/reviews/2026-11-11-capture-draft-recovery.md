# Task capture draft recovery — November 11, 2026

**Result: Pass with follow-ups.** Pending-save review now uses a separate panel without replacing an open project draft. Forms with a pending operation resolved elsewhere remain locked and ask the user to close and inspect the task list. The change distinguishes a form's own recovery updates from changes reported by another view. This is not complete task-editor acceptance.

On macOS Darwin arm64, `npm --prefix frontend test` passed 205 tests in 19 files and `npm --prefix frontend run typecheck` passed. A React test simulates a second-window storage event and confirms the separate draft remains after the pending task is recovered. Actual multi-window behavior, reload/restart, rendered widths/themes, keyboard, failure recovery, live service integration and user review remain open. No production build or personal data was used.
