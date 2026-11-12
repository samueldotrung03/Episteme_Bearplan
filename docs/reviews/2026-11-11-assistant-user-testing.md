# Assistant actions — user testing, November 11, 2026

**Gate:** partial run of [G-06](../GATES.md#gates-that-block-the-alpha) (Assistant
daily writes beyond create, Apply/Undo and completion). **Result: G-06 not
passed.** Two of six requests behaved correctly; four found defects that need
fixes before G-06 can be retried. The fix plan is in [GATES.md](../GATES.md#planned-fixes-from-g-06-testing-nov-11).

**Who and how.** The user typed the requests below into the in-app Assistant
on a project named "Testing" with tasks "Test #1" and "Test #2". The data
instance, port and model were not recorded in the session. Root causes were found
by an agent reading the code (no code was changed and no tests were run for this
record). Service Today was 2026-11-11 (a Wednesday).

## Results

| # | User request (as typed) | What happened | Verdict |
| --- | --- | --- | --- |
| 1 | "check the todos for next week" | "There are no tasks matching "next week" in the "Testing" project with an incomplete status." | **Defect** (A-01) |
| 2 | "add the task under testing as "Test#2" on Wednesday , Nov 18th 2026 and the due day is Nov 20th 2026" | "Please ask for one change at a time. I can create a task, …" | **Defect** (A-02) |
| 3 | "Check the remained tasks" | Correct list across all projects: Test #1 (Testing, incomplete, due 2026-11-12), Test #2 (Testing, incomplete, due 2026-11-11) | Correct answer; user found that deadlines are not guarded against past dates (A-03) |
| 4 | "mark the "Test #1" task in "Testing" project" | Prepared the completion of Test #1 | **Correct** ("GOOD!") |
| 5 | "mark the "Test #1" task in "projecting" project" | Offered to complete Test #1 although it is in Testing, not "projecting" | **Defect, wrong record risk** (A-04) |
| 6 | "start tracking "Test #1" in testing for 30'", then pause, then "Resume the test #1" | Start and pause worked; resume answered "How many minutes should the countdown run (1–180)?" | **Defect** (A-05) |

## Root causes (from code reading)

- **A-01, "next week" read as a title.** The router copied "next week" into the
  task (search words) slot; grounding kept it because the words are in the
  message. Nothing turns "this/next/last week" into a date range:
  `parse_day` (`backend/domain/action_library.py`) does not accept it and the
  direct plan answer returns early on relative words
  (`backend/domain/assistant_answers.py`, `_plan`). The model specialist then
  also limited the search to Testing, most likely from the selected context,
  despite the prompt rule that selected context is not a filter
  (`backend/domain/assistant.py`, `SYSTEM`).
- **A-02, create with a planned day rejected.** The router prompt classifies
  "create and plan it" as `multiple` (`assistant.py`, `ROUTER` example), and
  `create_task` has no planned-day slot (`action_library.py`, `LIBRARY` and
  `ALLOWED`), although the app's task form already saves a task and its planned
  day in one request (`frontend/src/TaskCaptureForm.tsx`). A second, hidden
  defect: `parse_day` rejects a weekday in front of a date ("Wednesday, Nov 18th
  2026"), so the date would fail even with the slot.
- **A-03, past deadlines accepted.** `_clean_deadline` (`backend/domain/tasks.py`)
  checks only that the value is a real date. Note: the planned-day rule it was
  compared to blocks *closed weeks* (`backend/domain/planning.py`,
  `_require_open_week`), not past days. The two deadlines shown in test 3 were
  today (2026-11-11) and tomorrow, so neither was actually in the past.
- **A-04, named project ignored.** `ALLOWED["complete_task"]` drops `project`, and
  the project in the message is used only to narrow several same-title matches
  (`action_library.py`, `evaluate` → `resolve_task`). With one "Test #1", the
  wrong project was never checked. The same applies to every action on an
  existing task (update, plan, complete, start timer).
- **A-05, no resume action.** The timer and its route support resume
  (`backend/domain/timer.py`, `backend/routes/timer.py` `/{session_id}/resume`),
  but the router has no resume intent (`assistant.py`, `INTENTS`), so "Resume"
  was classified as `start_timer`, which needs a duration.

## Also noticed (minor)

- Test 3 listed the task due 2026-11-12 before the one due 2026-11-11; the list
  is not ordered by deadline (A-06).
