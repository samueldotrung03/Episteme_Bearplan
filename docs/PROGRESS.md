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

**Next concrete step:** Complete real browser verification of storage/lock failures,
broader keyboard/accessibility and theme coverage, and user acceptance using the
[UX handoff](../frontend/BEARPLANS_UX_HANDOFF.md). The task-entry integration
remains in progress.

## Open follow-ups and gates

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
- Decisions still open: assistant defaults 2–6 in the [actions review](reviews/2026-11-01-assistant-actions.md);
  UX draft row/breakpoint measurements, cross-month week filing, Earlier selection,
  and Figma font fallback. Do not treat proposed defaults as user decisions.

## Refinement plan (tracking and release readiness)

Separate from the active UX slice. Entry point:
[docs/plans/refinement](plans/refinement/README.md); board and handoff log in its
[STATUS.md](plans/refinement/STATUS.md). Active: RF-01 (rebaseline the roadmap),
roadmap rewritten, waiting on the user's target dates. Next: write the dates in,
then RF-02. RF-04 (new core-trial candidate) waits for the task-entry slice to close.

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
