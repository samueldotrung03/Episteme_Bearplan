# Today task-list implementation — first UX slice

**Pass with follow-ups.** On macOS 26.6.2 arm64, implemented the task-list
portion of the reviewed [Today design](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=5-3972)
using its existing React/CSS conventions and task/placement APIs. Today uses the
service date and existing task identity, displays project/parent context and an
accessible Start control, and groups completed work behind a disclosure with
compact, checked, struck-through reopen controls. It retains failed-save errors,
disables mutations while the planner is unavailable or saving, and moves focus
to the disclosure or reopened task after a successful refresh. Completion uses
the November 11 timer-finalization rule.

The existing Week and Projects interfaces remain visible below this first slice.
This is not full Today-screen fidelity or full redesign acceptance: compact
navigation, Today/Week switching, prominent streak, project drawer, Earlier
unfinished, planned-week Done, atomic task/planning save, persisted ordering,
secondary screens and the remaining responsive/accessibility reviews are open.
Service-day rollover during an indefinitely open page also needs review. Figma's
old session-preservation text is superseded by the user's later timer decision.

## Verification

- `npm --prefix frontend test -- --run`: 182 passed. The initial run found three
  duplicate error-announcement failures; the shared planner error now has one
  alert and the final suite passed. `npm --prefix frontend run typecheck` and
  `npm --prefix frontend run build` passed.
- Guarded Chrome regression on the intermediate build: 17 passed covering
  existing project, timer, Settings and Today paths.
- Final built UI: `BEARPLANS_E2E_CHANNEL=chrome BEARPLANS_EVIDENCE_DIR=
  /tmp/bearplans-today-final-lock .venv/bin/python -m pytest -q -p no:cacheprovider
  -p tests.connections_sandbox tests/test_today_browser.py --tb=short` — 3 passed.
  It checked 640×900 light, 1440×900 dark, completion/reopen and keyboard focus,
  plus seven-task reachability and Start at 640×800. Light and dark screenshots
  were visually inspected; temporary evidence may expire. No user acceptance,
  full screen-reader run or full UX parity is claimed.
- No backend, schema, user database, provider or preserved trial copy changed.
