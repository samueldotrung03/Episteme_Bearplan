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

## Expanded create-failure reproduction and recovery design

Fake-provider tests now also reproduce duplicate project lists, BearPlans
calendars and timed events when a remote create succeeds but its local mapping
write fails. On macOS arm64, the guarded command
`.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_tasks.py tests/test_google_calendar.py`
reported 33 passed and five strict xfails. The first run had an XPASS caused
by the list test targeting the wrong list; establishing the default-list mapping
first corrected the fixture. All five xfails document unresolved failures.

The independently reviewed repair direction is an account-scoped durable intent
written before each remote create. Record only the operation and local/container
identities; never store titles, notes or credentials. Publish the returned mapping
and resolve the exact intent together in one short transaction, outside provider
calls. An unresolved intent must survive failure, restart, target edits/deletion,
disconnect and account changes; it must block ambiguous automatic and manual
retries. Account A → B → A must not discard A's pending intent. A crash before
sending can be indistinguishable from a lost successful response, so recovery
cannot rely on titles or assume no remote write occurred.

A user-facing reviewed recovery is still needed: explain that a remote copy may
already exist, that no remote object was deleted, and that retry after explicit
resolution may create a duplicate. Revalidate the verified account and the exact
pending operation/review revision under the provider lock and write transaction;
make repeated resolution safe. This is a design direction, not implemented or
approved as a completed feature. The test matrix must cover journal write failure,
pre-request crash, lost response, mapping-write rollback, restart, account changes,
local edits/removal, Pause, repeated recovery and all four resource types.

Google's [Calendar event creation guide](https://developers.google.com/workspace/calendar/api/guides/create-events)
describes client-generated event IDs as a way to prevent duplicates after an
uncertain create. Its [event resource reference](https://developers.google.com/workspace/calendar/api/v3/reference/events)
adds format and collision-detection qualifications. Whether and how to use that
mechanism requires separate design and tests; it does not resolve the other three
resource types by itself.
