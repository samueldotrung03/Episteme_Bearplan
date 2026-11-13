# Assistant G-06 fixes A-02, A-03, A-01, A-06 — November 12, 2026

**Gate:** [G-06](../GATES.md#gates-that-block-the-alpha) stays **open (not passed)**
until the user retries the [six requests](2026-11-11-assistant-user-testing.md#results).
A-04 and A-05 were fixed on November 11 (commit `98e0f78`). This record covers the
remaining planned fixes from [GATES.md](../GATES.md#planned-fixes-from-g-06-testing-nov-11).
Work on macOS, disposable data only. Not committed.

## Acceptance scenarios (user's exact wording)

| ID | Request | Now |
| --- | --- | --- |
| A-02 | `add the task under testing as "Test#2" on Wednesday , Nov 18th 2026 and the due day is Nov 20th 2026` | One card: *Create task "Test#2" in Testing, planned Wed 2026-11-18, due Fri 2026-11-20*. One Apply saves the task and its planned day together; one Undo removes both |
| A-03 | A deadline before today | Refused by the Assistant, `POST/PATCH /api/tasks` and `POST /api/task-captures`, with “The deadline … is before today (…). Choose today or a later date.” Today is allowed (user decision, Nov 11) |
| A-01 | `check the todos for next week` | Direct answer, Mon–Sun next week, across all projects: “Planned that week” and “Due that week, not yet complete”, labelled (user decision, Nov 11) |
| A-06 | `Check the remained tasks` | Direct answer (“remained” now recognized), earliest deadline first, then title |

## Changes and decisions

Implementation decisions below are the agent's (proposed), within the plan the
user approved in GATES.md; the two user decisions are marked confirmed.

- **A-02.** `create_task` takes an optional planned day (`planned_date`), saved in
  the same transaction as the task through the shared `_create_placement_tx`, as
  the task form does. The receipt stores both IDs; Undo removes the plan and the
  task only while both are unchanged (a moved plan refuses Undo and changes
  nothing). No schema change: the receipt kind is still `create_task`.
  - `parse_day` accepts a weekday before a date; a disagreeing weekday asks
    (“November 18, 2026 is a Wednesday, not a Thursday. Which date do you mean?”).
  - Measured with qwen3:8b: the router dropped the deadline from the user's
    message, and “under testing as "Test#2"” was read as a parent task. Code now
    reads day words after “due/deadline” and “on/for” only when they parse as a
    day, a quoted title after “as”, and treats “under X” as a project when X is a
    project name and no top-level task has that exact title.
  - Grounding refuses a planned day whose words appear only after “due”, so a
    deadline is never also planned.
- **A-03.** `require_deadline_not_past` applies where a person enters a deadline
  (task API create/edit, task capture, Assistant create/edit), not in the shared
  write helpers, so imports (Google Tasks, bCourses) and Undo keep stored dates.
  Editing other fields, or resending the same stored overdue deadline, is
  allowed. A capture retry of an earlier save still replays after its deadline
  day has passed. The task forms show the server's message; no `min` was added
  to their date inputs (those files hold the uncommitted task-entry dialog work).
- **A-01.** `parse_week` turns this/next/last week into a Monday–Sunday range.
  Week or day words are never used as title search words. Project filtering only
  when the user names a project. `list_tasks` gained optional `due_from`/`due_to`
  so the source card shows the exact range read. A plan-only week question
  (“What is planned next week?”) gives the existing week plan answer directly.
- **A-06.** `list_tasks` deadline order breaks ties by title; incomplete-task
  answers use it.
- **Router prompt `router-v9`.** “Create Outline and plan it on Friday” is now a
  create example; a new example creates with a planned day and deadline;
  “Complete Essay and start Math for 30 minutes” is the `multiple` example; the
  tasks topic includes what is due. v9 first filed “What is due soonest?” under
  time (M5 R8 failed, 29/30); code now moves a due/deadline question without
  time words from time to tasks, and the prompt names deadlines under tasks.
- **Tests with fixed past deadlines.** Thirteen API, restart and browser test
  files sent fixed deadlines (October 2026, or days away); they now use 2099
  dates so they neither fail now nor expire. A failing assertion inside the real
  launcher restart test left its server running and hung the whole suite for over
  an hour; that run was stopped and the stray test servers ended by PID.

## Checks (macOS)

- Focused: `tests/test_assistant_actions.py`, `tests/test_assistant_answers.py`,
  `tests/test_assistant.py`, `tests/test_deadline_not_past.py`, capture tests: pass.
  New tests replay the user's wording (A-02 with three router variants, including
  the live one; A-01 with the user's run where “next week” was copied as a title).
- `tools/m5_evaluation.py --model qwen3:8b`, router-v9 final: **30/30**, no
  unauthorized changes (first v9 run 29/30, see above).
- Live replay through the full pipeline with qwen3:8b on disposable data
  (Today 2026-11-12): A-02 proposal, Apply (task + plan), Undo (both removed);
  A-01 two labelled lists across projects; A-06 ordered list; past deadline
  blocked; weekday conflict asked.
- Full `python3 tools/check.py` (disposable data): **exit 0** in 313.9 s — typecheck,
  214 frontend tests, build, 1175 backend/browser tests passed, 1 skipped.

## Gaps

- G-06 needs the user's retry in the app (about 20 minutes).
- The live model can still classify some create-and-plan wordings differently;
  the code fills only stated, parseable day words, and every change needs Apply.
- Date pickers do not yet prevent choosing a past deadline before Save.
