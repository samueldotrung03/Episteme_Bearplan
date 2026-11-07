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

## Independent review and blocker — November 6

An independent review of the committed Settings and connections delivery found
that Google task creation is not replay-safe when the provider has created an
item but the local mapping write fails. The reviewer reproduced two synthetic
remote tasks after retry using a disposable database and in-memory provider.
A lost create response has the same ambiguity. Source inspection found the
same remote-create-before-local-mapping window for task lists, calendars and
calendar events; those three paths have not yet been individually reproduced.
Matching by title alone cannot safely establish identity. This blocks the
SYNC-09 and SYNC-12 retry acceptance and APP-C08.3 delivery pass.

The independent reviewer ran the guarded connection suite: 121 passed on
macOS with local loopback access. An earlier sandboxed run had 17 failures and
104 passes because loopback listeners were denied; it was rerun successfully.
No real provider or credentials were accessed.

Two strict expected-failure regression tests now document task mapping-write
and lost-response windows. On macOS arm64, the command
`.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_tasks.py`
reported 17 passed, 2 xfailed. Expected failures are open defects, not passes.
A durable repair must cover both uncertainty windows, restart, and all affected
create types without guessing identity or duplicating existing user data.

The reviewer also found outdated bCourses error recovery text. Missing and
rejected token messages now point to Settings. The guarded command
`.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_bcourses.py tests/test_connections.py`
passed 53 tests. Error codes and credential storage were unchanged.

The VoiceOver and operator gates remain open. The former disposable local
VoiceOver app was no longer listening when checked and must be recreated.
A check of 207 relative links across the README, progress, delivery review and
Settings planning documents found no missing local targets.
