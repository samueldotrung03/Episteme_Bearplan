# B3 — saved within-day order

## Authorization and scope

On November 14, 2026, the user said: “Yes. I know six user-owned gates are open
(G-14, G-15, G-16, G-04, G-05, G-06). My override still applies to B3 only.”
The user also confirmed that timed tasks can be freely reordered while retaining
their start time, and date moves carry that time. Backend only; frontend integration
and shared progress/gate updates are assigned to the coordinating lane.

Migration 0026 was free on main and this branch when checked. It adds a position
table keyed by active placement ID, initialized per day by existing creation time
and row order. Original placements and closed snapshots remain unchanged. New
placements and reviewed carryover append; deletion compacts; legacy date moves append. Reordering and
positioned date moves update both day orders in a serialized transaction. Closed
weeks retain the order captured in their snapshot, including legacy snapshots.

## Route contract

`GET /api/planning` retains existing fields and adds `position` to placement
objects (zero-based integer for active placements, nullable for old snapshots).
The active placement array is ordered by date and position. Existing
`PATCH /api/placements/{id}` remains compatible and appends a date move.

`PUT /api/placements/{id}/order` accepts JSON:
`{"planned_date":"YYYY-MM-DD","position":0,"source_order":[{"id":"...","revision":1}],"destination_order":[{"id":"...","revision":1}]}`.
Each order is the full ordered list the client read for that day, including the
moved item in the source. For same-day reorder both arrays are identical. The
position is the zero-based insertion index after removing the moved item. On
success HTTP 200 returns the updated Placement. An unchanged position is a no-op.
The client should refresh planning after success to receive all affected positions.

HTTP 409 `placement_order_conflict` means either reviewed list or a revision
changed; refresh and retry. HTTP 409 `placement_conflict` means the task already
has a placement on the destination date; `week_conflict` means a closed week or
archived placement. HTTP 422 `invalid_input` covers invalid IDs, dates, positions
and request shapes; HTTP 503 `storage_unavailable` covers storage failures. None
of these failures partly changes either day. Existing host/origin checks apply.

## Verification and handoff

macOS (Darwin), disposable databases, no real secrets. Focused command
`.venv/bin/python -m pytest -q tests/test_placement_order.py tests/test_planning_api.py tests/test_migrations.py`:
61 passed. The first full check passed frontend typecheck, 217 frontend tests and
build but failed one schema-23 test that compared a pre-upgrade placement against
the new additive position field (1180 passed, 1 skipped). The assertion was
updated to check the initialized position. A second run was interrupted after
finding that carryover also needed to append positions. The sandbox blocked a
focused local-service socket test; its unrestricted rerun passed. After the fix,
`.venv/bin/python -m pytest -q tests/test_placement_order.py tests/test_weeks.py tests/test_task_capture.py`
passed 94 tests, including real-service restart, migration rollback/retry and
carryover replay. Final full `python3 tools/check.py` passed:

```text
PASS            frontend typecheck       0.4s
PASS            frontend tests           9.5s — 217 passed (217)
PASS            frontend build           0.6s
PASS            backend tests          316.6s — 1184 passed, 1 skipped in 315.87s (0:05:15)
check: all 4 steps passed in 327.0s
```

Result: **Pass with follow-ups** for the backend slice; integrated frontend
behavior and user acceptance remain open.

Proposed gate row (no ID): User; accept within-day ordering after the frontend
connects it; on disposable data reorder timed and untimed rows, move across days,
try cancellation and a stale view, and check a closed week; about 15 minutes;
blocks acceptance of integrated ordering; evidence this review and future frontend
review; open upon integrated delivery. Next: frontend lane consumes the contract.
