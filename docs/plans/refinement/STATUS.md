# Refinement plan — status and handoff log

Read this first in every session; update it last. Ticket details are in
[TICKETS.md](TICKETS.md). States: `Ready`, `In progress`, `Waiting on user`,
`Blocked`, `Done`, `Deferred`.

## Board

| Ticket | Title | State | Depends on | Waiting on the user for |
| --- | --- | --- | --- | --- |
| RF-01 | Rebaseline the roadmap | Waiting on user | — | Target dates (asked 2026-11-11) |
| RF-02 | Gate register and limit on waiting work | Ready | RF-01 helps | Which gates to defer; rule wording |
| RF-03 | Decision sheet for the user | Ready | — | Answers to each decision |
| RF-04 | New core-trial candidate and trial start | Blocked | UX task-entry slice closed | Trial scope; tag; Day 1 |
| RF-05 | Repository cleanup | Ready | — | Approval to move duplicates; push |
| RF-06 | One command for every check | Ready | — | Hook and CI, yes or no |
| RF-07 | Documentation map | Ready | RF-02 (links to gate register) | — |
| RF-08 | Closing re-evaluation | Blocked | RF-01 to RF-07 | — |

## Handoff log (newest first)

Copy this template for each session. Keep an entry under 20 lines.

```
### YYYY-MM-DD — <agent> — <ticket> — <state at end>
- Did: <what changed, one or two lines>
- Files: <exact paths created or edited>
- Checks: <command → result; say "not run" if not run>
- Not done: <what remains inside this ticket>
- Waiting on user: <questions asked and not yet answered>
- Next step: <the first concrete action for the next session>
- Watch out: <anything surprising in the tree; other agents' uncommitted work>
- Commit: <not committed; proposed message given to user | committed by user as <hash>>
```

### 2026-11-11 — Claude — RF-01 — Waiting on user
- Did: steps 1–5 done in `BearPlans_Dated_Roadmap.md`: dated status paragraph, "Current
  plan" (Now/Next/Later), "Milestone status" table, October table kept as history with
  four marks corrected (Oct 26, Oct 28, connection setup → ✅; Oct 30 → ◐).
- Files: `BearPlans_Dated_Roadmap.md`; this file; `docs/PROGRESS.md` (pointer section only).
- Checks: link check → all 28 relative links exist and are tracked in Git. Rows
  cross-checked against `605826e:docs/PROGRESS.md` build status and COMPLETED.md headings.
- Not done: step 6. The four "Next" rows say "date not set".
- Waiting on user: target dates for the four Next steps (proposed Nov 14 / Nov 16 /
  Nov 17–23 / Nov 24).
- Next step: write the user's dates into the "Next" table, re-run the link check, then mark Done
  and add a COMPLETED.md entry.
- Watch out: handoff said 3 untracked task-capture reviews; there are 4 (keyboard-layout
  added, 208 frontend tests). Uncommitted edits by others in `BearPlans_Build_Plan.md`, `CLAUDE.md`,
  `docs/COMPLETED.md`, `docs/PROGRESS.md`, google-sync review. Build plan heading
  "Connection setup … not started" is stale (Settings delivered); left for RF-02/RF-07.
- Commit: not committed; proposed message given to user.

### 2026-11-11 — Claude — plan created — no ticket started
- Did: wrote this folder from the November 11 evaluation; added a pointer
  section to `docs/PROGRESS.md`; added an untracked personal `CLAUDE.local.md`.
- Files: `docs/plans/refinement/{README,TICKETS,STATUS,BASELINE,PROMPTS}.md`,
  `docs/PROGRESS.md` (pointer section only), `CLAUDE.local.md`, `.git/info/exclude`.
- Checks: backend 1,102 passed and 1 skipped at commit `77f7ebf`; frontend 207
  passed on the current working tree. Backend not re-run after `77f7ebf`.
- Not done: no ticket has started.
- Waiting on user: nothing yet.
- Next step: RF-01, step 1 (recover the build-status table from `605826e`).
- Watch out: uncommitted task-entry work in `frontend/src/App.tsx`,
  `App.test.tsx`, `TaskCaptureForm.tsx` and three untracked reviews belongs to
  the active UX slice. `main` is 54 commits ahead of the remote.
- Commit: not committed.
