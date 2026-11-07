# Google uncertain-create review controls

**Pass with follow-ups for the recovery surface; sync protection is not implemented.**
On macOS 26.6.2 arm64, added an explicit reviewed resolution for a durable
pending create. The server verifies the current provider account under the
connection and provider locks, then checks the exact account-bound review key
inside a serialized write. A stale, repeated or different-account confirmation
cannot clear a newer intent. Resolution changes only the local intent: it does
not identify, link or delete any Google object. The user must accept the
possibility of a duplicate. A mismatch returns a structured 409 error.

Settings and Google show a generic prompt before verification after restart;
local item details remain hidden until the saved owner is verified. Google
then shows current local context (which may have changed), a fallback for removed
work, and a review dialog explaining possible duplicates and manual cleanup. Cancel preserves the
intent. The UI disables manual sync while a pending intent is visible. Pause is
preserved. These controls are not proof that a pending intent stops background
or API sync: the existing create paths do not yet use the intent journal.

Independent review identified the need for local context, explicit no-link
wording and the paused-restart verification entry. These were added. A final
read-only review found no additional blocker in these controls and prompted the
current-context and matching-name cautions. It also
confirmed that integration into all four create paths and guarding background
sync remain necessary. No real provider or personal data was accessed.

Checks:

- `.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_create_intents.py tests/test_google_account.py tests/test_google_controls.py tests/test_connections.py tests/test_google_tasks.py tests/test_google_calendar.py` — 136 passed, 5 expected failures (the original duplicate-create cases).
- `npm --prefix frontend test` — 180 passed; `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` passed. An initial test used the unpaused button name; the corrected paused-state test passed.
- `BEARPLANS_E2E_CHANNEL=chrome .venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_browser.py::test_uncertain_create_review_after_restart_while_paused` — 1 passed in Chrome at 640 × 800 with a disposable database and fake providers. Verified hidden details before account verification, contextual review, Escape/focus return, confirmation and no provider writes.

Still required: journal all four creates and atomically publish mappings,
block manual and automatic sync before any mutation on pending intent, validate
target/parent after provider calls, handle malformed responses and storage
failures, and verify retry/restart/account-switch/race cases. Rerun independent
review and browser/theme/assistive-technology checks after integration. The
five expected failures and delivery blocker remain open.
