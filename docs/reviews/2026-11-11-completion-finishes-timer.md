# Local task completion also saves its timer

**Pass with follow-ups.** Product decision, November 11: completing a task
should finish its matching active timer like Finish early and record time spent.
The user confirmed Needs review must be resolved in Track first. This supersedes
the earlier local-completion rule preserving active timer controls.

## Delivered behavior

The local completion endpoint and Assistant Apply use the TimerService lock and
a serialized write transaction to save task completion, finalized intervals,
existing tree outcome and captured-rate coin award together. The live clock is
reconciled first. Running and paused sessions save confirmed time; unknown gaps
require Track review. Other tasks' timers are untouched. Natural countdown expiry
retains its completed outcome. No schema or existing data migration is required.

Assistant completion proposals explain the timer consequence. Apply checks the
matching session identity/revision as well as task revisions. Receipts preserve
replay; failed finalization rolls back task changes and in-memory anchors. Undo
reopens only the task; saved time and its finalized session remain. The interface
refreshes the timer after local task changes. Lower-level task-only helpers and
Google-imported completion ticks retain their existing behavior; this ticket
changes user-initiated local UI and Assistant completion.

## Verification

macOS 26.6.2 arm64, disposable databases/fake clocks/providers and installed Chrome.

- Affected backend tests (`tests/test_assistant_actions.py tests/test_timer.py
  tests/test_timer_api.py`, guarded pytest): 116 passed in 7.07 seconds. Initial
  attempts exposed obsolete preservation expectations and two assertions using
  a nonexistent public microseconds field; those tests were corrected.
- Three additional focused checks passed in 0.31 seconds: running/paused credit
  and captured-rate award, stale session refusal, and replay without finalization.
- `npm --prefix frontend test -- --run`: 180 passed; typecheck and build passed.
- `tools/m5_evaluation.py --model qwen3:8b --output
  /tmp/bearplans-completion-finish-evaluation.json`: 30/30; routing 100%, zero
  unauthorized changes. Temporary evaluation evidence may expire.
- Focused real Chrome checks for Assistant Apply/Undo and weekly-card completion:
  two passed in 4.48 seconds. An old exact-summary assertion was updated for the
  reviewed timer consequence.
- Final affected backend run after the in-transaction clock recheck: 117 passed
  in 7.72 seconds. The broad rerun started before that final clock refinement;
  these focused tests exercise the final completion path.
- The first full guarded run had 1,100 passes, one Windows-only skip and one
  obsolete exact-summary assertion failure; its corrected browser test passed
  separately. Clean rerun: `BEARPLANS_E2E_CHANNEL=chrome .venv/bin/python -m
  pytest -q -p no:cacheprovider -p tests.connections_sandbox --tb=short` —
  1,102 passed, one Windows API-only skip in 238.00 seconds.
- The user replied “ok good” to the changed completion/Undo walkthrough. A
  follow-up read after restarting the disposable service found no active session,
  a saved finished_early outcome with 1.67511 confirmed seconds, and the task
  reopened. This is user-reported feedback plus API state, not a directly observed
  UI walkthrough; this does not certify Mac sleep hardware,
  real providers or release/core-trial acceptance.
