# APP-C08.1 — Integrated process, fault and regression review

**Pass with follow-ups.** macOS 26.6.2 arm64, Python 3.13.15, Node 24.21.0
and installed Chrome. The run used disposable data and fake provider
credentials and adapters. Base revision was `8e7a136` plus the tests in this slice.

- A real BearPlans process saved Google Pause, a task and its dated placement.
  After abrupt termination, a second process returned the same Pause
  timestamp and plan. Resume persisted through a graceful stop and a third
  process read back the unchanged plan. This case ran without a Google
  grant. Signed-in Pause, Sync once and Resume were exercised separately
  with fake Google clients in the browser and domain suites.
- A fake calendar read failure left the prior recurring-event cache intact.
  Retry accepted a moved occurrence and removed a canceled one while
  preserving the previously added task, its fields and its placement.
  Adding the moved occurrence again returned the same task.
- The full suite exercised bCourses setup, replacement faults, course review
  and explicit Add; Google setup, denied and delayed authorization, partial
  sync, retries, same-account reconnect and account isolation. It also ran the
  existing SQLite migration, backup, offline Plan, closed week and timer
  regressions, including the real countdown with the browser closed.

## Commands and results

- `npm --prefix frontend test` — 178 passed in 16 files.
- `npm --prefix frontend run typecheck` — passed.
- `npm --prefix frontend run build -- --outDir /tmp/bearplans-c081.8ONaRb` — passed.
- Initial full suite with `pytest.main`, `backend.platform.paths.FRONTEND_DIST`
  set to that build, `BEARPLANS_E2E_CHANNEL=chrome` and
  `-q -p no:cacheprovider -p tests.connections_sandbox` — 1,041 passed,
  one skipped. Launcher regression cases refreshed the checkout's generated
  frontend build during this pass.
- Full suite with `BEARPLANS_E2E_CHANNEL=chrome .venv/bin/python -m pytest -q
  -p no:cacheprovider -p tests.connections_sandbox` in a temporary copy of the
  tracked source and virtual environment — 1,041 passed, one skipped in
  221.55 seconds. The same fresh frontend was installed under the temporary
  copy's `frontend/dist` before startup so child processes served the matching
  build from the start. The sole skip in both runs required the real Windows API.
- `.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox
  tests/test_google_reading.py
  tests/test_service_restart.py::test_google_pause_and_local_plan_survive_abrupt_service_restart`
  — 9 passed. This focused run also includes the recurring-event case added
  after the full suite collected its tests.
- Scoped diff and documentation links checked.

APP-C08.2 covers measured layout, zoom, keyboard and assistive-technology
evidence. The real-process case demonstrates local durability. Signed-in
account isolation across app reconstruction uses fakes, and real OAuth,
provider operation, operator acceptance and Mac sleep/wake remain separate gates.
