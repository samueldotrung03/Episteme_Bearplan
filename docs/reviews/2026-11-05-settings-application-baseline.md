# APP-C01 — Settings application baseline and test fixtures

November 5, 2026. **Pass with follow-ups** for baseline reconciliation and in-process
fixture readiness (DOC-01, DOC-02 and the DATA-01 relocation baseline). The user’s
“continue” after the design publication selected APP-C01. Codex reviewed the source
and ran the checks on macOS 26.6.2 (Darwin arm64), Python 3.13.15 and Node 24.21.0.
The repo was at `83fdbfe` with the account guard below still in the working tree.
No normal app instance or real account participated.

## Checkout and existing capabilities

- `f375f24` moved the credentials into the private data folder and added the
  one-time legacy copy marker. `674db93` added the write-only
  [connection setup routes](../../backend/routes/connections.py).
- `a43a456` added saved Google Pause and status, an in-flight wait, and local
  disconnect with best-effort revocation. It also made a different OAuth client
  file save before sign-out so a failed file write can keep the previous setup.
- The [Google routes](../../backend/routes/google.py) and
  [sync service](../../backend/domain/google_tasks.py) already support the three
  connected functions. The [bCourses routes](../../backend/routes/bcourses.py)
  already expose courses, assignment review and explicit Add. The current
  [React shell](../../frontend/src/App.tsx) retains separate Google and bCourses
  work tabs. The [API client](../../frontend/src/api.ts) and the old tabs have
  yet to adopt the setup routes, Pause/status and account recovery.
- The concurrent account patch adds migration 21, primary-calendar hashing,
  mismatch status, a guard on full sync and live calendar readers, and explicit
  adoption that clears previous provider links locally. Its five fake-account
  tests passed. Preserve this work for reconciliation in APP-C02.4, including
  the migration, rather than building a second account mechanism. The tracked
  Google route/domain diff had SHA-256
  `058ee1ef2c7d205f52cbe13bf42a4fbb85d180be443ee02d4e828610bbdd3d90`.
  The untracked account module, migration and test were also present. Unrelated
  planning, Claude, backend review and duplicate files stayed outside APP-C01.

## Contract and test routing

Read the authoritative [CON requirements](../../frontend/plans/settings-connections/SPEC.md#requirements),
[case definitions](../../frontend/plans/settings-connections/TEST_PLAN.md) and
[reviewed Figma starts](../../frontend/plans/settings-connections/HANDOFF.md#open-this-version)
together. These are source observations and routing for future acceptance.

| Requirement and design example | Reusable baseline and remaining work | Application cases |
| --- | --- | --- |
| CON-01 · FIG-01/04/05 · local lifecycle and offline return | Local service owns sync. Keep cache and work available on failure. Verify browser close, process restart, stale status and work return separately. | C04/C05/C08/C09 · SYNC-01/07/12, UI-10, DATA-08, LIVE-04 |
| CON-02 · FIG-01/04 · status and offline | Reuse `/api/connections` metadata, Google status and `paused_at`/last attempt/last success/last error. Present setup, auth, operation, preference and evidence separately. A valid file or successful Resume response establishes only that step. | C03/C05/C07 · DOC-03, UI-01/06, API-01/05/10, SYNC-12 |
| CON-03 · FIG-02 · token save, rejected token, Keep token | Existing validation and bounded check preserve the old token on rejection or unavailable check. Token and metadata writes are separate. Define recovery if the token writes and status publication fails. Keep retry text masked in the open dialog. | C02.1/C05/C06/C08 · API-02/04/09, UI-02, DATA-01–03 |
| CON-04 · FIG-02 · courses and review | Keep course choices, cache, due-date review and explicit Add. The old bCourses view refreshes on first visit with a token and no attempt. Verify the manual Refresh contract as Settings and the work destination are integrated. | C06/C07 · UI-07, SYNC-07–08, DATA-06 |
| CON-05 · FIG-03 · Google file setup | Reuse parser, owner-only file write, and same-client retention. Validate replacement and recovery across file, authorization and status, including partial publication. Client ID and file validity convey different information from Google consent. | C02.1/C05/C07/C08 · API-03/04/09, UI-03, DATA-01–03 |
| CON-06 · FIG-03 · scope, waiting, missing permissions | Reuse existing local callback and attempt invalidation on disconnect. Verify denial, timeout, supersession and explicit cancellation. The draft sign-in UI needs a backed cancellation path before claiming success. | C02.2/C05/C07 · API-05–07, UI-04–05, DATA-03 |
| CON-07 · FIG-03 · calendar picker and sync scope | Keep calendar reads, BearPlans-calendar publication and all-task Tasks export together in the consent explanation. Imported bCourses tasks participate after Add. Reuse mapping, completion and event identity. Retain last complete success on partial failure and test retry convergence. | C06/C07/C08/C09 · UI-08, SYNC-08–12, DATA-06, LIVE-03 |
| CON-08 · FIG-04 · Pause, Sync once, Resume | Worker policy is persisted and automatic worker entry checks it under lock. Explicit sync keeps it paused. Mounted calendar refresh and acknowledgement under contention need work. | C03/C04/C07/C08 · API-10, UI-06, SYNC-01–06, DATA-03–04 |
| CON-09 · FIG-04/05 · disconnect, offline revocation, removal | Reuse local disconnect and revocation receipt. Coordinate in-flight sync/auth with replacement and remove. Retain task/history/cache and remote copies. Show revocation confirmed, unavailable or unattempted accurately. | C02.1–3/C05/C07 · API-04/06/07, UI-02–03/05/08, SYNC-12, DATA-05–06 |
| CON-10 · different-account reference in FIG-03 | Draft guard covers common A/B and same-account paths. Missing identity falls through, and migrated links have no proved first binding. Review cache visibility and require fresh candidate identity before applying adoption. | C02.4/C07/C08 · API-08, DATA-07 |
| CON-11 · FIG-01/05/06 · Settings navigation, long courses, Dark, return to timer | Add the Settings entry and dialogs with keyboard/error/focus handling. Preserve selected work and session identity across entry/exit. Check arbitrary resize, zoom and assistive technology on the real UI. | C05/C08 · UI-09–10, DATA-05/08 |
| CON-12 · all fixed examples · privacy | Existing private files and loopback/origin protections apply. Keep credentials out of responses, artifacts, backups and Assistant tools. | C02/C03/C08/C09 · DOC-01–04, API-09, DATA-01–02, applicable LIVE cases |

## Decisions and failure boundaries

- Confirmed: one Settings entry, separate credential dialogs, durable Google
  Pause across restart, and Sync once preserving Pause. All automatic entry-point
  gating, waiting before Pause acknowledgement, explicit calendar work while paused
  and fresh reconciliation on Resume retain the spec’s proposed detailed semantics.
- The dedicated bCourses review destination is still proposed. Keep the current
  review reachable until the replacement is agreed and implemented. Widths/themes
  are Figma reference cases. Proposed production measurements and typography can
  be resolved when scoping the shell.
- Reproduced the sync barrier gap with the lock held and `wait_seconds=0`:
  `GoogleSyncService.while_idle` still executed its callback. APP-C02.3/C04.3
  need an honest busy/retry outcome or a successful barrier. Cover disconnect,
  replacement/removal and account adoption callers when changing that helper.
  APP-C04.2 owns `Google.tsx` opening with an empty cache and the distinction
  between automatic and explicitly requested calendar reads.
- Account recovery requires a separate slice. Before granting access to old
  mapping/cache data, handle an unverifiable identity and migrated links, verify
  the current auth attempt and candidate at Apply, and test overlapping IDs and
  restart. Recovery by returning to the original account should preserve valid
  mappings. The draft adoption resets local links and requires explicit reviewed
  scope before being exposed in Settings.
- Credential/status files, OAuth attempt and token cache, Google Pause and sync
  records, and provider links/caches are the affected records in later slices.
  Settings or provider removal must preserve local task and placement IDs, session
  state and immutable week snapshots. Source Add and Google leaf completion
  remain separate existing domain operations.

## Fixture setup and verification

Use [the opt-in sandbox](../../tests/connections_sandbox.py) with the existing
`tests/conftest.py` disposable DB and fake revocation. It points data and credential
resolution at pytest temporary paths and rejects non-loopback HTTP requests through
the stdlib transport the adapters share. Fake bCourses, Tasks, Calendar, OAuth
exchange and revocation are supplied by the existing tests. The real OAuth callback
test uses loopback with a fake exchange. The guard is in-process. For a later
subprocess or browser check, supply disposable paths and fake provider transports in
that process too. In particular, keep the secrets override set so standalone startup
skips legacy credential copy. DATA-01 deliberately unsets it only with a disposable
data root and explicit synthetic legacy source.

For later timing cases, reuse the fake timer clock in
[the timer tests](../../tests/test_timer.py) and event barriers from
[Google control tests](../../tests/test_google_controls.py). Inject times and
release points at each affected boundary. More extensive fixtures with overlapping
provider IDs, stale account candidates, partial publication and closed-week/timer
invariants belong to the slices that exercise them.

```sh
# probe_dir held a one-test assertion that HTTPS to a synthetic .invalid name is blocked
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox \
  "$probe_dir/test_outbound_guard.py" tests/test_connections.py tests/test_secrets_location.py \
  tests/test_bcourses.py tests/test_google_tasks.py tests/test_google_calendar.py \
  tests/test_google_reading.py tests/test_google_controls.py tests/test_google_account.py
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build -- --outDir "$bp_build_dir"
git diff --check
```

- Backend: **97 passed**, including five existing relocation tests and the
  temporary outbound-guard probe. The first sandboxed run passed 96 and failed
  the OAuth callback bind with EPERM. The scoped rerun allowed loopback and passed.
- Frontend: **166 passed across 15 files**. Typecheck and build passed. Initial
  Vitest and build attempts hit EPERM writing Vite’s temporary config in the
  checkout. The reruns had write access for Vite’s temp files. Build output
  went to a fresh temporary directory.
- DOC-01/02: contract/route mapping, link and case reference checks, and scoped
  whitespace/diff review passed. Fixture coverage is a baseline for the current
  application. The Settings interaction, process-level restart, live-provider,
  and real browser/accessibility cases remain future work.

## Next slice

APP-C02.1, bCourses credential replacement fault recovery first. Exercise an
existing valid token, an accepted replacement and a status-write failure after
the new token is saved. Prove the previous credential remains usable or show a
truthful recoverable state, then retry to a single valid save. Cover rejected and
offline checks, write-only responses and origin checks with synthetic canaries
(API-02/04/09, DATA-02/03). Scope Google replacement separately because it crosses
auth and sync boundaries.
