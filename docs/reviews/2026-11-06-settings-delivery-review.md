# Settings delivery review

**In progress.** This is a self-review by the implementing agent on macOS
26.6.2 arm64. The independent final review remains open.

The committed Settings range from `88203e4^` through `6d72f36` was
checked for whitespace errors. Reviewed the connection settings, bCourses
course selection, Google account adoption and disconnect paths, and the
shared completion adapter. Account adoption checks the reviewed account key
again and clears connection links and source cache in one transaction. Local
tasks remain separate from those cleared tables. The UI describes that
consequence before confirmation. Disconnect reports whether Google confirmed
revocation. Parent task completion continues to derive from subtasks.

A fresh guarded fake-provider run passed 121 cases:
`.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox
tests/test_google_account.py tests/test_google_controls.py tests/test_google_tasks.py
tests/test_connections.py tests/test_google_reading.py`. These cases exercise
account isolation, stale review, credential faults, Pause, disconnect,
cross-export, retries and calendar cache behavior. The earlier
[integrated review](2026-11-06-settings-integrated-regression.md) contains
full-suite results. The [accessibility review](2026-11-06-settings-accessibility-review.md)
contains browser and zoom evidence.

The VoiceOver walkthrough, independent review and operator/live evidence are
still open. A passing fake-provider suite does not establish those results.
