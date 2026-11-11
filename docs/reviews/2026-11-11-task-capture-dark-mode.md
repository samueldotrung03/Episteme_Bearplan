# Task capture dark-mode recovery — November 11, 2026

**Result: Pass with follow-ups.** On macOS Darwin arm64, used Chrome's DevTools `prefers-color-scheme: dark` emulation in a disposable test tab against a schema-24 local service. The browser reported the dark media query active, body background `rgb(22, 25, 23)` and viewport 589×1167 with DevTools docked. No system appearance setting or personal data was changed; closing the tab ended the override.

Inspected the empty form and an interrupted save. The title and notes remained visible, the error and Check save status control were readable, and the page did not overflow horizontally at this viewport. The error text computed as `rgb(255, 138, 143)` on the form's `rgb(22, 25, 23)` background. After restarting the service, activating Check save status with Enter saved the synthetic task and returned visible focus to Add task. This outage occurred before the request reached the service; post-commit replay is covered by the [separate-window review](2026-11-11-task-capture-separate-windows.md).

The service was stopped and test tab closed. This is one compact dark viewport and a bounded visual/keyboard check, not a complete contrast audit, screen-reader test or dark-theme matrix. Actual browser storage/lock faults, wider accessibility coverage and user acceptance remain open. No application code changed in this check.
