# BearPlans — open gates

Created November 11, 2026 (refinement ticket RF-02). A **gate** is a check that
must pass, or be explicitly deferred by the user, before something counts as done.
This file is the one list of open gates. Sources: `docs/PROGRESS.md` ("Open
follow-ups and gates"), the historical snapshot `605826e:docs/PROGRESS.md`
("Next up", "Open follow-ups", "Pending manual gates") and the reviews linked below.

**Classes.** *Blocks the trial*: must pass before the seven-day core trial can
start. *Blocks the alpha*: must pass, or the feature must be left out, before the
personal alpha decision (target Nov 24). *Accepted as unverified*: the user
chose not to require the check; it blocks nothing and has not passed.
Time estimates are rough and unverified. No gate here has passed. The limit
on waiting work is in [AGENTS.md](../AGENTS.md#open-gates-and-the-limit-on-waiting-work):
no new build while more than three user-owned gates block the trial or the alpha
(four on November 11: G-03 to G-06; three from November 14 after G-03 passed; four again after G-14 opened the same day).

## Gates that block the trial

| ID | What must be checked | Owner | What to do, roughly how long | Blocks | Evidence | Opened |
| --- | --- | --- | --- | --- | --- | --- |
| G-14 | You accept the Atelier Today dashboard and new app bar (A0 + A1) | User | Open the app on disposable data, add two or three tasks for today (one with a start time), then look at Today in light and dark mode: use ↑/↓, Enter, X, N, W, P, open Completed, and check bCourses/Google are reachable from Settings. Say "accept" or what is wrong; about 15 minutes | Closing the Atelier A0 + A1 slice and the RF-04 trial candidate; the next Atelier slice (A2) | [Review](reviews/2026-11-14-atelier-today.md) | Nov 14 |
| G-15 | You accept the Atelier Week screen (A3) | User | Open the app on disposable data with a few tasks across the week (one with a start time, one completed), open Week in light and dark mode, use previous/next and "Back to this week", open a day's calendar events if Google is set up, complete a task and use Move or remove; check a narrow window too. Say "accept" or what is wrong; about 10 minutes | Closing the Atelier A3 Week slice | [Review](reviews/2026-11-14-atelier-week.md) | Nov 14 |
| G-16 | You accept Earlier unfinished on Today (B1 backend + Today frontend) | User | After the Today frontend shows it: on disposable data, plan tasks in the past, today/future and a closed week, then check the Earlier unfinished list and its controls; about 10 minutes. Cannot be checked until the frontend is connected | Acceptance of the integrated Today slice with Earlier unfinished | [B1 review](reviews/2026-11-14-b1-earlier-unfinished.md); future frontend review | Nov 14 |

## Gates that block the alpha

| ID | What must be checked | Owner | What to do, roughly how long | Blocks | Evidence | Opened |
| --- | --- | --- | --- | --- | --- | --- |
| G-04 | Seven days of real use of the core app | User | After RF-04 names a new candidate: follow the [trial guide](CORE_TRIAL_CHECKLIST.md), report Day 1 (date, data folder, backup result), then short daily notes and a closing review; about 30 minutes to start, 5 minutes a day | The alpha (M4 release). The Nov 1 candidate folder is superseded by RF-04 | [Trial guide](CORE_TRIAL_CHECKLIST.md) | Nov 1 |
| G-05 | End-of-week carryover, the Stats "Missed" count and the Assistant carryover command work in the app on real data | User | Run End Week once in the app, check the carried tasks and the Missed count, try the Assistant carryover command and Undo; about 15 minutes. Can be done during the trial | Carryover in the alpha | [Carryover review](reviews/2026-11-01-end-week-carryover.md); prototype walkthrough only in [UX-R23](reviews/2026-11-02-ux-r23-walkthrough.md) | Nov 1 |
| G-06 | Assistant daily writes beyond the scenarios already tried (create, Apply/Undo, completion) | User, then Agent | **Partly tried Nov 11: not passed.** Six requests, four defects (A-01–A-05 below). The agent fixes A-01–A-05 with tests; the user then retries the [six requests](reviews/2026-11-11-assistant-user-testing.md#results) plus edit and finish, with Apply and Undo; about 20 minutes | Assistant writes in the alpha | [Actions review](reviews/2026-11-01-assistant-actions.md); [Nov 11 walkthrough](COMPLETED.md#november-11-2026--assistant-create--apply--undo-walkthrough); [Nov 11 user testing](reviews/2026-11-11-assistant-user-testing.md) | Nov 1 |

### Planned fixes from G-06 testing (Nov 11)

Agent-owned work, not separate gates; G-06 stays open until the user's retry
passes. Order: A-04 first (it can change the wrong record), then A-05, A-02,
A-03, A-01. Each fix gets backend tests that replay the user's exact wording;
the full `python3 tools/check.py` run is required before handoff.

| ID | Defect | Planned fix | User decision |
| --- | --- | --- | --- |
| A-04 | A named project is ignored when acting on an existing task ("Test #1 in projecting" was offered for completion) | **Fixed Nov 11, awaiting your retry.** Accept `project` for every action on an existing task. If the project does not exist, say so; if the task is not in it, say where it is ("Test #1 is in Testing, not Projecting") and offer no Apply | No |
| A-05 | "Resume" asks for a countdown length | **Fixed Nov 11, awaiting your retry** (schema migration 25, approved by the user). Add a `resume_timer` intent with no required details, like pause: resume the paused countdown or say nothing is paused. Uses the existing timer resume | No |
| A-02 | "Create Test#2 on Wednesday, Nov 18th 2026, due Nov 20th 2026" is refused as two changes | **Fixed Nov 12, awaiting your retry.** Let `create_task` take an optional planned day and propose one change (create and plan, one Apply, one Undo), matching the app's task form. Teach `parse_day` to accept a weekday before a date and ask when they disagree. Update the router example that calls this `multiple` | No |
| A-03 | A deadline before today can be saved | **Fixed Nov 12, awaiting your retry.** Reject a newly entered or changed deadline before today in the API, the form and the Assistant. Keep stored overdue deadlines valid when other fields are edited, and keep imported (Google Tasks, bCourses) past deadlines | Decided by the user, Nov 11: a deadline of today is allowed ("YES") |
| A-01 | "Todos for next week" searched for a task titled "next week" and limited itself to one project | **Fixed Nov 12, awaiting your retry.** Parse this/next/last week as a Monday–Sunday range in code; never use date words as title search words; keep searches across all projects unless the user names one | Decided by the user, Nov 11: show both, labelled — tasks planned next week and tasks due next week ("YES") |
| A-06 | Task lists are not ordered by deadline (minor) | **Fixed Nov 12, awaiting your retry.** Order incomplete-task answers by deadline, then title | No |

## Gates accepted as unverified (not open)

Each of these covered a feature that can be left out of the alpha, or a condition
with no known way to test it. **User decision, November 11, 2026:** first "We can
wait for these all", then "yes accept them as unverified". All six are accepted
as unverified: they no longer count as open gates or block anything. They have
**not passed**. No review, roadmap or alpha decision may describe these checks as
passed or verified; say "accepted as unverified by the user, Nov 11, 2026".
Rows are kept so the check can still be run later; a later pass moves the row to
[COMPLETED.md](COMPLETED.md) with its evidence.

| ID | What must be checked | Owner | What to do, roughly how long | Blocks | Evidence | Opened | User decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G-07 | Standby type 5 (one Mac sleep mode) keeps timers correct | User decides | No supported way to put this Mac into that mode was found; decide whether to accept it as unverified; 1 minute | Full M2/M3 hardware certification | [Standby assessment](reviews/2026-11-01-standby5-capability.md) | Nov 1 | Accepted as unverified, Nov 11 |
| G-08 | bCourses works with your real token: course selection, assignment review, Add | User | Requires your real token and separate permission; about 20 minutes. Fake-token setup already passed | bCourses in the alpha | [bCourses review](reviews/2026-11-01-bcourses-connection.md), [operator walkthrough](reviews/2026-11-10-settings-operator-walkthrough.md) | Nov 1 | Accepted as unverified, Nov 11 |
| G-09 | Google Calendar/Tasks work with your real account, including signing in again with the same account | User | Requires your real account and separate permission for any remote writes; about 30 minutes | Google sync in the alpha | [Google sync review](reviews/2026-11-02-google-sync.md), [settings handoff](../frontend/plans/settings-connections/IMPLEMENTATION_HANDOFF.md) | Nov 2 | Accepted as unverified, Nov 11 |
| G-10 | The app behaves well when the whole Mac is offline | User | Turn off Wi-Fi, use the app and the Settings connections, turn it back on; about 15 minutes | Connections in the alpha | [Settings handoff](../frontend/plans/settings-connections/IMPLEMENTATION_HANDOFF.md) | Nov 6 | Accepted as unverified, Nov 11 |
| G-11 | Known risk: continuing an interrupted Google create can make a duplicate remote item | User decides | Decide whether to accept this known limitation; 1 minute | Google sync in the alpha | [Create-guard review](reviews/2026-11-06-google-create-guard.md) | Nov 6 | Accepted as unverified, Nov 11 |
| G-12 | Design and runtime acceptance of the rest of the UX redesign (UX-06–36: Plan, Week, history and secondary screens) | User and Agent | Per screen, after each is rebuilt; hours in total | The finished redesign, not the alpha | [PROGRESS](PROGRESS.md) "Open follow-ups and gates" | Nov 2 | Accepted as unverified, Nov 11 |

## Found in the same lists but not gates

Recorded so nothing is lost; they are tracked elsewhere.

- **Decisions** (Assistant defaults 2–6; UX row height, breakpoint, cross-month
  weeks, Earlier selection, Figma font fallback): refinement ticket RF-03.
- **Missing features**: applied-action history view; earlier unfinished,
  planned-week Done and within-day ordering. Product work, not checks.
- **Documentation map** (frontend/backend/shared-tests ownership): RF-07.
- **Housekeeping**: Codex's project registration still names the old nested
  folder; the user reopens `/Users/hiberkeley/Desktop/Projects/Episteme_Bearplan`.

## How to update this file

Every delivery that leaves a user check open adds a row here. When a gate
passes, delete its row and record the pass in [COMPLETED.md](COMPLETED.md) with
the evidence. When the user defers a gate or accepts it as unverified, move it
to the matching section with the date and the user's words. A gate that blocks
neither the trial nor the alpha and that the user has not yet decided goes in a
"can wait" section (none exists today).
