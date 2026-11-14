# Atelier redesign A3: Week — review

November 14, 2026. Source design: Figma *BearPlans — Atelier redesign (Test 1)*,
Screens page, frame `43:8441` "S2 Week / ideal · planned week" (file
`Sxhit2hudslGGvwqkxpX8G`). [Plan](../../frontend/plans/atelier-redesign/PLAN.md).
Started on the user's override ("Override, start Week", Nov 14) with four user-owned
gates open (G-14, G-04, G-05, G-06). Frontend only; no API, schema or saved-data
change. A2 (Today data gaps) was skipped because it needs the backend lane.

## What changed

- **Header.** The week heading is the date range ("Nov 9 – 15", "Oct 26 – Nov 1",
  with years across a year boundary) and a muted "N of M done". Week navigation is
  a previous icon button, "Back to this week" (was "Today") and a next icon button,
  followed by the shared Today/Week, Projects and Add task controls, as on Today.
  The section is still the "Weekly plan" region (now by `aria-label`).
- **Status line.** Open/closed badge, "Weekly completion: … work items complete
  (…%)" and the progress bar stay, restyled as one compact line under the timezone
  note. Closed-week history and closed-week text are unchanged.
- **Day columns.** No column boxes. Header: short day and date ("Mon 9"; today is
  an ink pill, with ", Today" for screen readers) and load "count · planned time"
  ("2 · 1h 20m", "0"). An empty day shows "—" (screen readers still hear "Nothing
  planned").
- **Calendar events.** Moved to the top of each day. Still one closed "From your
  calendar (N)" disclosure (user decision, Nov 3: a busy week has about 28 events),
  now a wood strip; opened rows use the wood bar instead of the calendar's own
  colour, per the Figma event-row rule. "Add as task" is kept.
- **Week card.** Hairline white card, 12 px padding. Top row: grip, start time (ink)
  and context; title in 14 px medium with a round checkbox (as on Today); meta line
  "30 min estimated · Due …"; quiet "Start tracking" and "Move or remove" text
  actions. Completed cards stay compact and struck through.
- **Narrow widths.** The existing day selector and single-day view are kept,
  restyled with Atelier tokens (selected day = ink).
- **Icons.** `chevron-left.svg` and `chevron-right-md.svg` downloaded from the
  frame into `frontend/src/assets/atelier/`.
- **Focus.** Today and Week each render the plan view controls, so switching view
  from a control now moves focus to the matching control in the visible view
  (`App.tsx`), instead of leaving it on the page.

## Deliberate differences from the frame

- Events stay closed by default (user decision above); Figma shows them open.
- Cards keep the checkbox, "Start tracking" and "Move or remove" so completing,
  tracking and date/time changes still work from Week; Figma's card has none.
  The grip stays visible and left of the context (existing grip decision and
  test), not only on focus.
- Wording kept for continuity: "30 min estimated · Due Nov 18, 2026" rather than
  "30 min · due Nov 18"; the completion sentence and badge are kept as well as the
  "N of M done" title.
- Not built (need data/backend): bCourses Source mark, Sync mark ("Changed in
  bCourses", "Moved in Google"), "Move to…" menu, Undo after a move, reorder within
  a day, the "+N more" overflow and the other S2 state frames (empty, loading,
  errors) beyond the existing behaviour.

## Checks (macOS, Nov 14)

- `npm run typecheck` passed; `npx vitest run`: 217 passed (App tests now use
  "Back to this week").
- Browser tests updated for the new labels/hooks: `test_weekly_browser.py`
  (region instead of heading; "Back to this week"; wait on the day column),
  `test_settings_browser.py` and `test_today_browser.py` (`.week-range`),
  `test_google_browser.py` (start time shown as "11:15 PM").
- Full `python3 tools/check.py`: all 4 steps passed (typecheck; 217 frontend tests;
  build; 1175 backend/browser tests passed, 1 skipped) in 313 s.
- Screenshots on disposable data (installed Chrome): 1440 light and dark, 800
  light, 640 dark; no horizontal overflow at any. Evidence:
  [screens](evidence/2026-11-14-atelier-week/).

## Not verified

- Closed-week (read-only) view and drag-in-progress styling were not compared with
  their S2 frames; covered only by the existing automated tests.
- Screen-reader operation and 200 % zoom.
- User acceptance: open as gate G-15.
