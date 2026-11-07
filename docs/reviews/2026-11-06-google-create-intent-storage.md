# Google create intent storage review

**Implementation slice: Pass with follow-ups. Delivery blocker remains open.**
On macOS 26.6.2 arm64, migration 23 adds a minimal account-bound intent table.
The domain primitive saves an intent only for the current account, rejects a
second unresolved intent for the same account, and publishes a mapping and
removes the exact intent in one transaction. Failed publication rolls back both.
Unresolved intents survive a database reopen and account changes. No task title,
notes or credential is stored in the intent. No provider call runs in a write.

This primitive is **not connected to Google sync**. It does not yet prevent any
remote retry, provide recovery controls, or resolve the existing five expected
failures. Do not consider the duplicate-write blocker repaired. A future slice
must wire all four create types, handle ambiguous outcomes, expose truthful
status and reviewed recovery, and test the full account/restart/race matrix.
Previously existing remote duplicates are not repaired by this migration.

Checks with disposable databases and guarded fake providers:

- `pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_create_intents.py tests/test_migrations.py tests/test_migration_fingerprints.py` — 32 passed before the additional upgrade test.
- `pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_create_intents.py tests/test_google_tasks.py tests/test_google_calendar.py tests/test_google_account.py tests/test_backups.py tests/test_api.py tests/test_instance_build.py` — 159 passed, 5 expected failures.
- `pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_create_intents.py tests/test_migrations.py tests/test_migration_fingerprints.py tests/test_google_account.py` — 46 passed, including failure/rollback of migration 23 and retry from a schema-22 disposable database.

Commands used `.venv/bin/python -m pytest`. The first broader run failed one
migration-22 fault test because its fixture injected into the last migration
instead of migration 22. The fixture was corrected and the broader run passed
as recorded above. No real Google calls or personal databases were used.
