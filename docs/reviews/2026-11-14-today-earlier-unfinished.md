# Today: Earlier unfinished and week dots (B1 frontend) — review

November 14, 2026. Source design: Figma *BearPlans — Atelier redesign (Test 1)*,
frame `32:1888` "S1 Today / partial · earlier unfinished" (file
`Sxhit2hudslGGvwqkxpX8G`). Backend contract:
[B1 review](2026-11-14-b1-earlier-unfinished.md). Authorized by the user on Nov 14
("Yes, do the Today wiring now") as work that lets gate G-16 pass; no new gate.
Frontend lane only; no backend, schema or saved-data change.

## What changed

- **API client.** `Planning.earlier_unfinished?: EarlierUnfinishedTask[]` in
  `frontend/src/api.ts`, matching the B1 route contract (optional, so an older
  service still loads).
- **Today.** Below Completed, an "Earlier unfinished · N" disclosure (closed by
  default; hidden when the list is empty). Rows use the Today row style: round
  checkbox, title, context "Project · Parent · from Thursday" (weekday within six
  days, otherwise "from Nov 5"), estimate. The checkbox completes the task.
  "Move to today" / "Move both to today" / "Move all N to today" adds a placement
  for today to each task (`POST /api/placements`), so earlier placements stay as
  history; the tasks then appear in today's list and the section disappears.
  A failure part-way shows an alert; tasks already planned show in today's list
  after the refresh.
- **Week dots (B2).** No change needed: Today already draws the seven dots from
  `GET /api/streaks` (last seven days ending service today; ink = qualified,
  wood = missed, ring = today). Figma's labels (M … S with today last) match this.
- **Icon.** `arrow-up.svg` downloaded from the frame into `frontend/src/assets/atelier/`.

## Deliberate differences from the frame

- The section is closed by default (Figma shows the open state of the disclosure).
- No per-row "move" control and no Start on earlier rows; Figma shows neither.
- bCourses Source/Sync marks remain unbuilt (need backend data).

## Checks (macOS, Nov 14)

- New frontend tests in `Today.test.tsx`: listing, context wording, completion
  request, "Move both to today" requests in order, and absence when empty. 219
  frontend tests pass.
- New browser test `test_today_earlier_unfinished_move_to_today` (375 dark, 1440
  light) on a real disposable service: two tasks planned 2 and 9 days ago appear,
  "Move both to today" puts both in today's list and removes the section.
  Evidence: [screens](evidence/2026-11-14-today-earlier/).
- Full `python3 tools/check.py`: all 4 steps passed (typecheck; 219 frontend tests;
  build; 1180 backend/browser tests passed, 1 skipped) in 319 s.

## Not verified

- Closed-week placements in the real interface (covered by the B1 backend tests).
- Screen-reader operation and 200 % zoom.
- User acceptance: G-16.
