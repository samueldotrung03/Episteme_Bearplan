# Atomic task capture API — November 11, 2026

**Result: Pass with follow-ups.** `POST /api/task-captures` accepts strict task fields, an operation ID and optional planned date; it calls the transactional domain function and returns the saved task and optional placement. The original task endpoint remains available. Existing structured validation, conflict, storage and same-origin protections apply. The task form is not yet connected; no UI behavior has changed.

## Verification

On macOS Darwin arm64, `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_task_capture_api.py tests/test_task_capture.py tests/test_api.py tests/test_tasks.py tests/test_planning.py tests/test_weeks.py tests/test_migrations.py` passed **268 tests**. API coverage includes normalized retry against a new app instance and reopened disposable database, changed-input conflict, replay after week closure, malformed input, parent constraints, rejected closed week and revised-date retry, injected storage failure and retry, and cross-origin rejection. No real provider or personal data was used. The full suite and a real process restart were not run for this slice.

Next: connect task entry with an optional planned day and stable operation ID; preserve input and support safe retries after an uncertain response. User acceptance remains pending.
