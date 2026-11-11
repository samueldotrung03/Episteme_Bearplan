# BearPlans — current progress

Updated November 11, 2026. Read [AGENTS.md](../AGENTS.md) before resuming.
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

**Next concrete step:** Complete real browser verification of storage/lock failures,
broader keyboard/accessibility and theme coverage, and user acceptance using the
[UX handoff](../frontend/BEARPLANS_UX_HANDOFF.md). The task-entry integration
remains in progress.

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
[DECISIONS_FOR_USER.md](plans/refinement/DECISIONS_FOR_USER.md). Next: RF-05 (repository cleanup).
RF-04 (new core-trial candidate) waits for the task-entry slice to close (target Nov 14).

## Handoff notes

- User data and credentials stay in the app data directory; do not use personal
  data for testing. The running disposable demo may use an older service; identify
  and restart it deliberately before testing a changed API.
- Preserve existing unrelated working-tree edits and `(1)` duplicate files.
  Do not push without a separate request. Review older planning statements against
  current product decisions and the linked evidence; preserve outstanding gates.
- A detailed historical status and delivery-register snapshot is available in Git
  as `605826e:docs/PROGRESS.md`. Completed entries and their original evidence
  remain in [COMPLETED.md](COMPLETED.md).
