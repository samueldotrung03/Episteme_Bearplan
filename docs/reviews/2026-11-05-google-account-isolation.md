# APP-C02.4 Google account isolation

November 5, 2026 · implementation review · **Pass with follow-ups**

BearPlans verifies the authenticated primary calendar before using saved Google
Tasks and Calendar links. An absent, blank or ambiguous identity blocks sync.
A different verified account can sign in, but it cannot use the previous
account's links or cache. The guard covers both Calendar and the Plan day
view. Cached events remain available offline for a verified grant. The same
account can verify again and continue using its links.
[Google CalendarList resource](https://developers.google.com/workspace/calendar/api/v3/reference/calendarList)

Account acceptance rechecks the current identity and the reviewed
owner/candidate pair before clearing the previous account's active local
links and cache in one transaction. The old remote copies and all local
tasks remain. If a preexisting set of links has no recorded owner,
BearPlans requires explicit review before starting fresh. Returning to a
previous account after starting fresh may create new remote copies because
the previous sync links were retired. BearPlans cannot reconstruct ownership
of links assigned by earlier builds.

Migration 22 scopes event-import identity to the verified account. It keeps
older import records and their tasks without assigning the owner by guess.
An older import may require manual recognition if the same event is offered
again. The existing Calendar follow and Plan Add actions carry the selected
account key, so stale actions cannot target overlapping IDs in a different
account. Publishing a new authorization waits for active Google work and
updates Plan's existing refresh signal. The Calendar view clears stale
selections when the sign-in state changes. Its automatic refresh respects
saved Pause, and explicit Refresh remains available.

## Verification

macOS 26.6.2 on arm64, Python 3.13.15, Node 24.21.0. The connection tests and
the Chrome Google flow used disposable paths and fake providers. The guard
blocked outbound urllib calls in those runs.

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox \
  tests/test_connections.py tests/test_secrets_location.py tests/test_bcourses.py \
  tests/test_google_tasks.py tests/test_google_calendar.py tests/test_google_reading.py \
  tests/test_google_controls.py tests/test_google_account.py
bp_test_data=$(mktemp -d /tmp/bearplans-account-final.XXXXXX)
BEARPLANS_DATA_DIR="$bp_test_data/data" .venv/bin/python -m pytest -q -p no:cacheprovider -m 'not e2e'
npm --prefix frontend test
npm --prefix frontend run typecheck
bp_build_dir=$(mktemp -d /tmp/bearplans-settings-build.XXXXXX)
npm --prefix frontend run build -- --outDir "$bp_build_dir"
git diff --check
```

- 145 guarded backend checks passed. API-08 covered reconnecting to the same
  account, mismatch, unverified identity, a stale approval after a third
  sign-in, overlapping event IDs, stale follow and Add, and token publication
  during active work. API-09 included foreign Origin on account acceptance.
- DATA-07 used fresh service objects and reopened SQLite files before and after
  the account change. Upgrades from schema 20 and 21 preserved legacy import
  IDs and task data. A fault during migration 22 rolled back to schema 21.
  Retrying the real migration succeeded and foreign keys were intact.
- The initial complete pytest run reported 1,019 passed, one Windows-only skip
  and one Google browser failure. Its fake auth only overrode the old connection
  check and its browser used the existing repository bundle. The browser fixture
  now seeds a disposable grant and still uses fake provider clients. The focused
  Chrome run passed at 1440 and 375 pixels with the final disposable production
  build. The harness set `backend.platform.paths.FRONTEND_DIST` before calling
  pytest on `tests/test_google_browser.py` with `-p tests.connections_sandbox`.
- The final non-browser pytest suite passed 999 tests, with one Windows-only
  skip and 21 browser cases deselected.
- 167 frontend tests passed across 15 files. Type checking, the disposable build,
  Git whitespace and review links passed.

## Handoff

APP-C03.1 is next for the Settings backend status contract. The account
confirmation UI remains part of APP-C07.4. Live Google identity and consent,
actual account recovery in Settings, and release acceptance remain open.
