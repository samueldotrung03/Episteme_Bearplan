# BearPlans — current progress

Updated November 12, 2026. Read [AGENTS.md](../AGENTS.md) before resuming.
Finished work and evidence are in [COMPLETED.md](COMPLETED.md); this file is the
single current handoff.

## Active work: task entry in the UX redesign

**Goal:** Save a new task and its optional planned day together from the project
task form. Preserve the entered details and make uncertain saves safely retryable.
The form is now connected in the working tree, but this slice is **not yet ready
for acceptance**: real browser checks remain open.

The atomic API and schema-24 transaction exist. The frontend recovery layer
persists the exact request and operation ID, coordinates same-origin windows with
Web Locks, and rechecks a definitive rejection before allowing replacement or
cancellation. Browsers without Web Locks fail closed. See the
[API review](reviews/2026-11-11-task-capture-api.md) and
[recovery review](reviews/2026-11-11-task-capture-recovery-followup.md).
The latest recovery checks passed 201 frontend tests and typecheck on macOS;
they did not test the integrated UI or actual browser windows. A stale window now
must identify the exact pending operation before retrying, checking or resolving it.
See the [cross-window review](reviews/2026-11-11-capture-stale-window.md).

The pending-save review now opens separately from project drafts. A simulated
second-window test confirms another open draft remains intact during recovery;
forms whose pending operation was resolved elsewhere remain locked and explain
how to close and check the task list. The full frontend suite passed 205 tests
and typecheck on macOS. [Review](reviews/2026-11-11-capture-draft-recovery.md).

The [browser check](reviews/2026-11-11-task-capture-browser-check.md) verified a
planned task, reload, cancellation and outage recovery across two tabs with a
separate draft, using disposable data. Production build, 205 frontend tests and
15 focused backend tests passed on macOS. This did not simulate a lost response
after commit or separate windows.

The [post-commit review](reviews/2026-11-11-task-capture-post-commit.md) verifies
lost-response replay across two tabs and documents fixes for a stale project list
and its refresh failure. Frontend: 207 tests and production build passed on macOS.

The [keyboard and layout review](reviews/2026-11-11-task-capture-keyboard-layout.md)
records a focus fix after successful Save and bounded light-mode form checks at
640, 800 and 1440 pixels. Frontend: 208 tests and build passed on macOS.

The [storage feedback review](reviews/2026-11-11-task-capture-storage-feedback.md)
records simulated form-level storage/lock failure checks and a clearer storage
error. Frontend: 210 tests and build passed on macOS. A separate-window browser
attempt was interrupted; no real storage/lock fault was verified.

The [separate-window review](reviews/2026-11-11-task-capture-separate-windows.md)
verifies a dropped committed response across two Chrome windows, preservation of
another draft and the original window's refresh; one task and receipt were stored.

The [dark-mode review](reviews/2026-11-11-task-capture-dark-mode.md) checks the
empty form and outage recovery at one compact Chrome viewport, including a visible
focus return. It is not a full theme or accessibility audit.

The [storage access review](reviews/2026-11-11-task-capture-storage-access.md)
records a fix for denied access to the browser storage property itself. A simulated
form check retains the draft and sends no request; 211 frontend tests and the
production build passed. A real browser storage fault remains unverified.

The [keyboard order review](reviews/2026-11-11-task-capture-keyboard-order.md)
checks Tab through the task form and Enter to save in the in-app browser, with
focus returning to Add task. Screen-reader operation and broader coverage remain open.

The [title accessibility review](reviews/2026-11-11-task-capture-title-accessibility.md)
records the associated title-length error and its correction, checked in the
in-app browser and a form test. The frontend suite passed 212 tests and build.

The [recovery focus review](reviews/2026-11-11-task-capture-recovery-focus.md)
records focus on Check save status after an outage and on the editable title
after a simulated definitive rejection. The browser outage recovery and 212
frontend tests passed; screen-reader and real storage/lock checks remain open.

The [closed-week focus review](reviews/2026-11-11-task-capture-closed-week-focus.md)
also verifies the rejection, recheck, focus return and corrected planned date in
the in-app browser using disposable data.

The [resolved-elsewhere focus review](reviews/2026-11-11-task-capture-resolved-focus.md)
records simulated checks that preserve focus in the affected form without stealing
it from another control. The 213-test frontend suite and build passed; a live
two-window check of this focus change remains open.

The [cross-tab focus review](reviews/2026-11-11-task-capture-cross-tab-focus.md)
confirms the Cancel focus in two live tabs. Closing the stale form exposed a
second focus gap; the fix returning focus to the project heading passed a live
two-tab browser recheck, the 213-test frontend suite and build.

G-02 passed its bounded keyboard and light/dark matrix at 640, 800 and 1440 px;
see the [matrix review](reviews/2026-11-11-task-capture-g02-matrix.md) for the
tested path and remaining accessibility limitations.

**Next concrete step:** Review the task-entry dialog with the user using the
[UX handoff](../frontend/BEARPLANS_UX_HANDOFF.md), including tasks with and without
a planned day, reload and retained drafts. G-03 remains open; the task-entry
integration remains in progress until that review is accepted.
For this review a disposable schema-24 instance was started on port 18992 with
data at `/private/tmp/bearplans-ux-dialog-review-20261111`; verify it is still
running and uses this data folder before relying on it.

On November 11, a joint walkthrough was started with a disposable schema-24
instance on port 18991, using `/private/tmp/bearplans-shared-check-20261111`.
The launcher rebuilt the interface successfully. Browser-control access was
unavailable in this session; the user was asked to try the task-entry acceptance
scenario directly. No acceptance has been recorded. G-01 subsequently passed
with a real Chrome storage-quota failure; see the
[quota review](reviews/2026-11-11-task-capture-real-quota.md).
Continue with the other user checks before the seven-day trial, as requested;
the old trial candidate and its checklist remain superseded by RF-04.

The user subsequently requested implementation of the remaining Figma UX in the
current project. The task-entry form now opens as a modal dialog. Escape or the
keep-draft control puts an unsaved draft aside while the page stays open; pending
save recovery retains its existing durable receipt and replay behavior. The
[dialog review](reviews/2026-11-11-task-entry-dialog.md) records bounded browser
checks and remaining acceptance. Continue the active slice before treating it as
accepted, then scope the remaining redesign under the open-gate rule. The user
requested the seven-day trial last.
The [alignment review](reviews/2026-11-11-task-entry-figma-alignment.md) records
partial 640 px light and 1440 px dark error-state inspection, passing focused
browser checks after updating stale tests, and the remaining verification.
The final `python3 tools/check.py` run passed typecheck, 213 frontend tests,
build and 1142 backend/browser tests (1 skipped), using disposable data on macOS.
The [G-13 matrix](reviews/2026-11-11-task-capture-g13-matrix.md) covered the
earlier inline form. The new dialog has separate bounded checks documented in
the [dialog review](reviews/2026-11-11-task-entry-dialog.md).

## Open follow-ups and gates

The register of open gates, with owners and actions, is [GATES.md](GATES.md); the
limit on waiting work is in [AGENTS.md](../AGENTS.md#open-gates-and-the-limit-on-waiting-work).
The bullets below are kept as context while the task-entry slice edits this file.

- The broader UX transformation and original UX-06–36 design/runtime acceptance
  remain open. Earlier unfinished, planned-week Done and within-day ordering
  require separate domain/persistence work. Continue the remaining Plan, Week,
  history and secondary screens after the active slice.
- Assistant creation, Apply/Undo and completion received bounded user walkthroughs;
  broader Assistant operator acceptance and the applied-action history view remain
  open. The user confirmed matching running/paused timers finish when their task
  is completed; Needs review must be resolved in Track first.
- **Assistant user testing, Nov 11 (G-06 partly tried, not passed):** of six
  requests, completion and the remaining-tasks list worked. Defects: a named
  project is ignored when acting on a task (A-04, wrong record risk); "Resume"
  asks for minutes (A-05); create with a planned day and deadline is refused as
  two changes (A-02); past deadlines are accepted (A-03); "next week" is searched
  as a title (A-01). Record: [user testing](reviews/2026-11-11-assistant-user-testing.md);
  fix plan and order in [GATES.md](GATES.md#planned-fixes-from-g-06-testing-nov-11).
  User decisions, Nov 11: a deadline of today is allowed (A-03); "todos for next
  week" shows both tasks planned and tasks due next week, labelled (A-01).
  A-04 and A-05 were committed (`98e0f78`; schema migration 25). A-02, A-03,
  A-01 and A-06 were fixed on Nov 12 in the working tree, not committed (router
  prompt `router-v9`; [review](reviews/2026-11-12-assistant-g06-fixes.md)): full
  `tools/check.py` passed and the live evaluation passed 30/30 with qwen3:8b.
  **Next: the user retries G-06** (the six requests plus edit and finish, with
  Apply and Undo; about 20 minutes) on a restarted disposable instance. Open
  follow-up: date pickers do not yet stop a past deadline before Save (the
  server refuses it). Disposable/demo instances on schema 24 upgrade to 25 when
  restarted with this build.
- Settings and connections were delivered with follow-ups. Real same-account
  reauthorization, real-provider verification and a system-wide offline operator
  test remain unverified and require separately bounded authorization. A reviewed
  Google-create continuation can still duplicate a remote item if one already exists.
  See the [implementation handoff](../frontend/plans/settings-connections/IMPLEMENTATION_HANDOFF.md).
- App hands-on checks of carryover/Missed and the Assistant carryover command remain
  open despite the successful bounded prototype walkthrough.
- The [seven-day local-core trial](CORE_TRIAL_CHECKLIST.md) has not been reported.
  Distinct Standby type 5 remains unverified; do not certify combined M2/M3 hardware
  or release readiness without its applicable evidence.
- The requested frontend/backend/shared-test ownership and documentation map is
  not started. Codex project registration still points at the old nested folder;
  reopen/select `/Users/hiberkeley/Desktop/Projects/Episteme_Bearplan` if needed.
- Assistant defaults 2–6 and the UX row height, cross-month filing, Earlier
  selection and Figma font were decided by the user on 2026-11-11 (rules in
  `AGENTS.md`; [decision sheet](plans/refinement/DECISIONS_FOR_USER.md)). The
  wide-layout width is to be set after a browser layout test; that test is open.

## Refinement plan (tracking and release readiness)

Separate from the active UX slice. Entry point:
[docs/plans/refinement](plans/refinement/README.md); board and handoff log in its
[STATUS.md](plans/refinement/STATUS.md). RF-01 (rebaseline the roadmap) is done;
target dates are in the roadmap's "Next" table. RF-02 is done: [GATES.md](GATES.md)
and the AGENTS.md limit. RF-03 is done: all ten decisions answered in
[DECISIONS_FOR_USER.md](plans/refinement/DECISIONS_FOR_USER.md). RF-05 (repository
cleanup): the [duplicate inventory](reviews/2026-11-11-duplicate-inventory.md)
found all 47 `(1)` paths redundant; they were moved out and the deletion was
committed and pushed (`6e5751c`), so RF-05 is done. RF-06: `tools/check.py` is
written and documented ([review](reviews/2026-11-11-rf06-check-command.md)); both
`--fast` and the full run pass, so RF-06 is done (user declined the hook and CI).
RF-07 is done: the [documentation map](README.md). Remaining: RF-04, then RF-08.
RF-04 (new core-trial candidate) waits for the task-entry slice to close (target Nov 14).

## Handoff notes

- User data and credentials stay in the app data directory; do not use personal
  data for testing. The running disposable demo may use an older service; identify
  and restart it deliberately before testing a changed API.
- Preserve existing unrelated working-tree edits. The `(1)` duplicate files were
  moved out of the repository on 2026-11-11 (RF-05,
  [inventory](reviews/2026-11-11-duplicate-inventory.md)); do not restore them.
  Do not push without a separate request. Review older planning statements against
  current product decisions and the linked evidence; preserve outstanding gates.
- A detailed historical status and delivery-register snapshot is available in Git
  as `605826e:docs/PROGRESS.md`. Completed entries and their original evidence
  remain in [COMPLETED.md](COMPLETED.md).
