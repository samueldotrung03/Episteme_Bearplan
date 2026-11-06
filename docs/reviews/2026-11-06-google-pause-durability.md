# Google Pause durability (APP-C04.1)

**Pass with follow-ups.** The existing migration 20 and transactional preference
write satisfy the durability slice. This change adds regression coverage in
[Google controls tests](../../tests/test_google_controls.py).

- A schema-19 database upgrades with automatic sync enabled by default. A
  schema-20 database retains its saved pause timestamp. The tests reopen each
  upgraded file twice and compare task records, task mappings, calendar
  selections, and last sync evidence. Foreign keys pass validation.
- A fault after the migration-20 ALTER rolls back the column and schema
  version. Retrying with the production migration succeeds.
- After shutting down the app instance, the test opens a new database handle
  and creates a fresh service. Pause remains visible and automatic task sync is
  skipped. A deliberate sync keeps the original timestamp. Resume persists
  through another reopen and automatic task sync becomes eligible.
- Injected Pause and Resume write failures return structured storage errors.
  Reopening the database shows the prior state, and retrying saves the change.

Verified on macOS 26.6.2 arm64 with disposable SQLite files and fake providers.
The outbound guard was enabled. The restart test uses fresh app and database
instances in the same process. Frontend, production code and migrations were
unchanged, so frontend and browser checks were outside this test-only review.

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_controls.py tests/test_google_account.py tests/test_google_tasks.py tests/test_google_reading.py tests/test_connections.py tests/test_migrations.py tests/test_migration_fingerprints.py
git diff --check
```

141 tests passed. Diff check passed. DATA-03/04 and API-10 are covered here for
preference persistence, upgrade and failed writes. APP-C04.2 still needs to
cover all automatic triggers, including calendar refresh on mount. APP-C04.3
owns Pause acknowledgement and concurrent actions. APP-C04.4 owns full
one-shot and Resume reconciliation. Live provider and operator checks remain
pending.
