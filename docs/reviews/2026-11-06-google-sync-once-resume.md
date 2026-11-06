# Google Sync once and Resume (APP-C04.4)

**Pass with follow-ups.** A deliberate full sync preserves the saved Pause
timestamp. Overlapping one-shot requests return a retryable busy error and do
not queue a second sync. A later deliberate retry is available after a failure.
The existing Google view labels the action Sync once while paused and discloses
that explicit calendar refresh and save each contact Google once.

Resume schedules reconciliation only when it clears a saved pause. A repeat
Resume leaves automation enabled and adds no wake. The reconciliation test
captured the scheduled wake and drove the automatic path explicitly. It
verified that multiple paused edits reconcile the final task title, completion,
and moved calendar event. Existing task and event mappings were reused and a
second automatic pass made no additional writes. Existing provider completion
and account rules remain in force. No schema changes.

On macOS 26.6.2 arm64, 48 guarded Google control tests and 177 frontend tests
passed. Type checking, a disposable production build and one guarded Chrome
Calendar-to-Plan walkthrough with simulated Google data passed. The full
non-browser backend suite passed with 1,012 tests, one Windows-only skip
and 21 browser tests deselected. The staged diff check passed.

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_controls.py
BEARPLANS_DATA_DIR=<disposable-directory> .venv/bin/python -m pytest -q -p no:cacheprovider -m 'not e2e'
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build -- --outDir /tmp/bearplans-c044-build.9nO70Q
git diff --check
```

The Chrome run used `tests/test_google_browser.py` and
`BEARPLANS_E2E_CHANNEL=chrome` with the temporary build. Settings controls
and live Google acceptance remain pending.
