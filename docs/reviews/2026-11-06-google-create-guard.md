# Google uncertain-create guard

**Implementation review: Pass with follow-ups.** On macOS 26.6.2 arm64,
Google sync now freshly verifies the account and checks for an unresolved
intent before applying remote completion or performing sync writes. Each
Google list, task, calendar and event create writes an account-bound intent
before the provider call. The mapping and intent resolution commit together.
A lost/malformed response, process interruption, changed target or failed
mapping leaves the intent for explicit review. Automatic and manual sync stop
before further sync writes while the verified account has an unresolved intent.
No network request occurs within a database transaction.

The review controls explain the possibility of an existing Google copy and
require account-bound explicit confirmation before clearing an intent. The
user can choose to continue with the acknowledged risk that the next sync
creates another copy. A guard cannot discover duplicates created before this
change, and it does not delete or link remote items on the user's behalf.
A crash before the request is sent can also require review because its outcome
is indistinguishable from a lost response. Provider and status-write errors
return structured, actionable messages; a calendar-stage error preserves the
fact that the Tasks stage already finished.

An independent read-only reviewer examined the create paths, account and
connection barriers, persistence, target/parent checks and error handling. The
review found no remaining confirmed blocker within this scoped implementation.
VoiceOver, real-account/operator evidence, the broader core trial and Mac
hardware/release gates remain separate and open. No real credentials, provider
requests or personal databases were used.

## Verification

- `.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox --tb=line` — 1,083 passed, 1 skipped (Windows API test) on macOS. Three later additions to the guard test module were checked separately after this run had begun.
- The complete `tests/test_google_create_guard.py` module — 20 passed. This covers all four creates with lost responses, malformed replies and failed mapping writes, plus failed intent writes, local target removal, account switching, automatic sync after restart, a separate Python process, unverified accounts and status-storage faults.
- Targeted Google intent, task, calendar, control and account tests — 124 passed. The five previously expected duplicate-create failures were replaced by assertions that retry stops; they are no longer expected failures.
- `npm --prefix frontend test` — 180 passed; `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` passed.
- `BEARPLANS_E2E_CHANNEL=chrome .venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_browser.py::test_lost_google_create_response_reaches_review_without_repeating tests/test_google_browser.py::test_uncertain_create_review_after_restart_while_paused` — 2 passed on the fresh production build, 640 × 800, disposable data and fake providers. One covered an actual simulated lost response and review; the other covered paused restart, account verification and Cancel/focus return.
- `git diff --check` passed. Earlier targeted runs exposed stale fixtures that bypassed account verification and outdated expected-failure tests; these were corrected. Two preliminary full-suite runs were deliberately interrupted to make review-driven changes; neither is counted as final evidence.
