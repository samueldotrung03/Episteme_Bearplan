# Task capture keyboard order — November 11, 2026

**Result: Pass with follow-ups.** On macOS Darwin arm64, used the in-app browser
and a schema-24 service on loopback with disposable data. Starting in the title
field, Tab moved through the date segments, estimate, planned-day segments, notes
and Add task. Enter saved a synthetic unscheduled task, the task appeared in Inbox,
and focus returned to Add task. The temporary tab was closed and service stopped.

The production build passed including typecheck. This bounded check does not
establish screen-reader operation, every keyboard path, all themes, or user
acceptance. Genuine storage and lock failures were not induced: the available
browser controls did not provide an isolated fault without changing the user's
browser settings. Simulated failures remain documented in the storage reviews.
