# BearPlans — current progress

Updated November 11, 2026. Read [AGENTS.md](../AGENTS.md) before resuming.
Finished work and evidence are in [COMPLETED.md](COMPLETED.md); this file is the
single current handoff.

## Active work: task entry in the UX redesign

**Goal:** Save a new task and its optional planned day together from the project
task form. Preserve the entered details and make uncertain saves safely retryable.
The form is now connected in the working tree, but this slice is **not yet ready
for acceptance**: cross-window draft/recovery navigation and real browser checks remain open.

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

**Next concrete step:** Fix and test the case where another window has a pending
save for a project whose task form already has a different open draft: reviewing
that pending save must not overwrite the draft or leave recovery inaccessible.
Then verify actual reload, two-window operation, UI and service together using
[UX handoff](../frontend/BEARPLANS_UX_HANDOFF.md), keyboard, widths and themes
with disposable data. Test storage/lock errors, cancellation and refresh failure.
The latest form tests cover one-request capture, lost response across remount and
closed-week correction; the full suite passed 204 tests before the last narrow
safeguard change, followed by 13 focused tests and typecheck. No production build
or user acceptance has been performed. [Working review](reviews/2026-11-11-task-capture-ui.md).

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
