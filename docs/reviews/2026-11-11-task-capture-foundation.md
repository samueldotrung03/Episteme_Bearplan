# Atomic task capture foundation — November 11, 2026

**Result: Pass with follow-ups.** Added a domain operation to save a task and optional placement with a durable replay receipt in one serialized transaction. Identical retries return the original task and placement, including after reopening the database; a reused key with changed normalized input conflicts. A closed week or failed placement rolls back task and receipt. Schema 24 adds the receipt table without modifying earlier migrations. This operation is not exposed by an API or used by the task form yet; it does not complete the user-facing One Save design.

## Verification

On macOS Darwin arm64, `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_task_capture.py tests/test_tasks.py tests/test_planning.py tests/test_weeks.py tests/test_migrations.py` passed **210 tests**, including concurrent replay, closed-week rejection, injected placement failure and retry, database reopen, and a disposable schema-23-to-24 upgrade preserving existing tasks and plans. An initial collection attempt used an incorrect function name and a later command named a nonexistent `test_storage.py`; both were corrected before the successful run. No personal data was used.

Next: expose a strictly validated API and build form-side operation-key retention, uncertain-result recovery, validation and user-visible planned-day control. Replay receipts intentionally return original save results even if records later change. Broader UI, full suite, actual app upgrade and user acceptance are not covered by these tests.
