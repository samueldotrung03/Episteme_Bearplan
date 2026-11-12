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
(four on November 11: G-03 to G-06).

## Gates that block the trial

| ID | What must be checked | Owner | What to do, roughly how long | Blocks | Evidence | Opened |
| --- | --- | --- | --- | --- | --- | --- |
| G-01 | Task entry keeps the typed task safe when browser storage or the cross-window lock really fails (so far only simulated) | Agent (UX slice) | Force a real storage/lock failure in Chrome with disposable data and record the result; about 1 hour | Closing the task-entry slice, so the new trial candidate (RF-04) | [Storage review](reviews/2026-11-11-task-capture-storage-feedback.md), [storage access review](reviews/2026-11-11-task-capture-storage-access.md) (in progress, uncommitted) | Nov 11 |
| G-03 | You accept the new task-entry form | User | Follow the [UX handoff](../frontend/BEARPLANS_UX_HANDOFF.md) with disposable data: add a task with and without a planned day, reload, and say "accept" or what is wrong; about 15 minutes | Same as G-01 | Asked for in [PROGRESS](PROGRESS.md) "Next concrete step" | Nov 11 |
| G-13 | Verify the changed task-entry presentation at compact and wide sizes in light and dark themes, including keyboard and error recovery | Agent (UX slice) | Open the current build with disposable data, inspect the form and its controls at 640, 800 and 1440 px in both themes, and check keyboard and failure recovery; about 1 hour | Closing the task-entry slice and the new trial candidate | [Progress](PROGRESS.md#active-work-task-entry-in-the-ux-redesign); the earlier [matrix](reviews/2026-11-11-task-capture-g02-matrix.md) predates the presentation change | Nov 11 |

## Gates that block the alpha

| ID | What must be checked | Owner | What to do, roughly how long | Blocks | Evidence | Opened |
| --- | --- | --- | --- | --- | --- | --- |
| G-04 | Seven days of real use of the core app | User | After RF-04 names a new candidate: follow the [trial guide](CORE_TRIAL_CHECKLIST.md), report Day 1 (date, data folder, backup result), then short daily notes and a closing review; about 30 minutes to start, 5 minutes a day | The alpha (M4 release). The Nov 1 candidate folder is superseded by RF-04 | [Trial guide](CORE_TRIAL_CHECKLIST.md) | Nov 1 |
| G-05 | End-of-week carryover, the Stats "Missed" count and the Assistant carryover command work in the app on real data | User | Run End Week once in the app, check the carried tasks and the Missed count, try the Assistant carryover command and Undo; about 15 minutes. Can be done during the trial | Carryover in the alpha | [Carryover review](reviews/2026-11-01-end-week-carryover.md); prototype walkthrough only in [UX-R23](reviews/2026-11-02-ux-r23-walkthrough.md) | Nov 1 |
| G-06 | Assistant daily writes beyond the scenarios already tried (create, Apply/Undo, completion) | User | Try the other everyday requests (change a date, start/pause/finish a timer, edit a task) with Apply and Undo; about 20 minutes. Can be done during the trial | Assistant writes in the alpha | [Actions review](reviews/2026-11-01-assistant-actions.md); [Nov 11 walkthrough](COMPLETED.md#november-11-2026--assistant-create--apply--undo-walkthrough) | Nov 1 |

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
