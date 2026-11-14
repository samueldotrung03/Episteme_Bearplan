# B1 Earlier unfinished — backend review

## Authorization and scope

On November 14, 2026, with four user-owned gates open (G-14, G-04, G-05,
G-06), the user said: “I am overriding the limit for this one build: start the
Earlier unfinished backend slice (B1) now, with the same limits as in my earlier
message.” This override applies to B1 only. The user reserved updates to the
shared progress, completed and gates files for main.

The read returns current incomplete leaf tasks with at least one saved placement
and no placement on or after service today, once per task. It includes both
active and closed-week placements, reports the latest date and current task,
parent and project details, and does not reschedule or write data. No migration
or saved-data changes. A closed future placement also excludes the task. There
is no archived-project state in the current project schema, so the requested
archived-project test cannot be constructed; closed-week archived membership is
covered instead.

## Route contract

`GET /api/planning?week=YYYY-MM-DD` (optional `week`, no request body) retains
all existing response fields and adds `earlier_unfinished`, an array independent
of the displayed week. Each item has `id`, `title`, `project_id`, `project_name`,
nullable `parent_id`, nullable `parent_title`, `last_planned_date`, nullable
`deadline`, and nullable integer `estimate_minutes`. Dates are YYYY-MM-DD.
The service's `today` and timezone determine the boundary; all planning data is
read in the same SQLite transaction. Results are sorted by latest planned date
descending, then title and ID. The existing route was extended rather than
adding a separate request. Invalid `week` produces HTTP 422 with existing
structured `invalid_input`; existing host and storage errors remain unchanged.
No new error codes or mutation operations are introduced.

## Verification and handoff

Environment: macOS (Darwin); disposable test databases and empty secrets.
Focused: `.venv/bin/python -m pytest -q tests/test_earlier_unfinished.py tests/test_planning_api.py`
— 39 passed. Tests exercise archived placements, multiple past placements,
today/future exclusion, completion, parent/leaf, current project details,
read-only behavior, service timezone midnight and the HTTP response.
After adding coverage for a historical leaf that became a parent and a closed
future placement, `.venv/bin/python -m pytest -q tests/test_earlier_unfinished.py`
passed all 3 tests.

The first full `python3 tools/check.py` run in the sandbox passed frontend
typecheck, 217 frontend tests and build, then failed backend tests: 42 failed,
1065 passed, 69 skipped and 2 errors. Process/socket permission failures
prevented service, OAuth and browser setup. The unrestricted full rerun passed:

```text
PASS            frontend typecheck       0.4s
PASS            frontend tests           9.0s — 217 passed (217)
PASS            frontend build           0.6s
PASS            backend tests          300.6s — 1178 passed, 1 skipped in 299.91s (0:04:59)
check: all 4 steps passed in 310.5s
```

Result: **Pass with follow-ups** for backend implementation; the integrated Today
interface and its acceptance remain future work.

**Proposed gate row (no ID):** Owner: User. Check: accept Earlier unfinished
in the Today interface after the frontend is connected. Action: use disposable
data to check past, today/future and closed-week plans and confirm the list and
controls; roughly 10 minutes. Blocks: acceptance of the integrated Today slice.
Evidence: this review and the future frontend review. Opened: upon integrated
delivery, not this backend-only handoff.

**Next:** integrate the additive response in the frontend under separately
authorized scope, then conduct the proposed user acceptance check. No claim of
frontend completion or gate passage is made here.
