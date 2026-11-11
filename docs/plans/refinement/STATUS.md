# Refinement plan — status and handoff log

Read this first in every session; update it last. Ticket details are in
[TICKETS.md](TICKETS.md). States: `Ready`, `In progress`, `Waiting on user`,
`Blocked`, `Done`, `Deferred`.

## Board

| Ticket | Title | State | Depends on | Waiting on the user for |
| --- | --- | --- | --- | --- |
| RF-01 | Rebaseline the roadmap | Done | — | — (dates set 2026-11-11) |
| RF-02 | Gate register and limit on waiting work | Done | RF-01 helps | — (answered 2026-11-11) |
| RF-03 | Decision sheet for the user | Done | — | — (answered 2026-11-11) |
| RF-04 | New core-trial candidate and trial start | Blocked | UX task-entry slice closed | Trial scope; tag; Day 1 |
| RF-05 | Repository cleanup | Done | — | — (moved and pushed 2026-11-11, `6e5751c`) |
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

### 2026-11-11 — Claude — RF-05 — Done
- Did: confirmed the user's commit `6e5751c` (4,457 files: 4,453 `(1)` deletions
  plus 4 docs) and push; `git rev-list --count origin/main..main` → 0; no `(1)`
  paths in `find` or `git status`. Closed board row; COMPLETED entry added.
- Files: this file; `docs/PROGRESS.md` (pointer); `docs/COMPLETED.md` (top entry).
- Checks: `git fetch`, `git log`, `git status`, `find`. No tests run (docs only).
- Not done: nothing in RF-05. No release tag exists yet (RF-04 covers the trial tag).
- Waiting on user: nothing.
- Next step: RF-06 (one command for every check), step 1 per TICKETS.md.
- Watch out: 4 backend browser failures from the previous entry are still
  unresolved (UX slice, Codex's area). RF-06's check script will hit them.
- Commit: not committed; proposed message given to user.

### 2026-11-11 — Claude — RF-05 — Waiting on user (commit + push)
- Did: step 4 after user's "yes": moved all 47 paths (`mv -n`, layout kept) to
  `~/Desktop/BearPlans-duplicates-2026-11-11/` (152 MB). They were *tracked*
  (committed in `5687685`, already on origin), so `git status` shows 4,453 ` D`
  files. History check redone excluding `(1)` paths: 112/114 match; the other two
  are older drafts of `7e38d7c` (see inventory correction). Step 6: PROGRESS
  handoff note updated. Step 5 credential check: only `backend/platform/secrets.py`
  and `tests/test_secrets_location.py`.
- Files: inventory (correction + move sections); `docs/PROGRESS.md` (pointer,
  handoff note); this file.
- Checks: frontend `npm test` 213 passed, `npm run build` ok; backend `pytest -q
  -p no:cacheprovider` **4 failed**, 1138 passed, 1 skipped (305 s). Failures:
  `test_add_task_disclosure_browser.py::test_add_task_retry_cancel_and_focus`
  [375-dark, 640-light, 1440-dark] and `test_e2e_browser.py::test_long_text_layout_and_keyboard_creation`;
  `get_by_role("alert")` with "Could not save task" not found. Very likely from Codex's
  `400bdfe` (committed mid-session; it changed TaskCaptureForm focus/errors),
  not the move: no test references a `(1)` path. Not proven by a pre-move rerun.
- Not done: user commits the deletion and pushes; then RF-05 can be Done.
- Waiting on user: commit + push (step 5).
- Next step: after the push, confirm `git status` has no `(1)` paths, `git
  rev-list --count origin/main..main` is 0, then close RF-05 (board, COMPLETED).
- Watch out: Codex is active (`400bdfe`; uncommitted G-02 matrix review, GATES.md,
  PROGRESS/COMPLETED hunks). Its G-02 review claims 640/1440 pass while the four tests above fail.
- Commit: not committed; proposed message given to user.

### 2026-11-11 — Claude — RF-05 — Waiting on user (inventory)
- Did: steps 1–3. Inventory of 47 `(1)` paths (6 folders, 41 files, ~152 MB):
  each source/doc copy matches a committed version; `.evidence` folders and
  sleep-probe logs match their ignored originals; the rest is generated output. None unique.
- Files: `docs/reviews/2026-11-11-duplicate-inventory.md` (new); this file;
  `docs/PROGRESS.md` (refinement pointer only).
- Checks: `git hash-object`/`git cat-file -e` per file; `cmp` and `diff -rq`
  against originals; `git check-ignore`. No tests run (nothing moved).
- Not done: step 4 move (after a yes), step 5 push (user), step 6 PROGRESS note.
- Waiting on user: yes/no to moving all 47 paths to `~/Desktop/BearPlans-duplicates-2026-11-11/`.
- Next step: on a yes, move with relative paths kept, then `git status` and both suites.
- Watch out: ticket said ~30 paths/120 MB; actual 47/152 MB. Codex's uncommitted
  work now includes five untracked task-capture reviews (last entry said three).
- Commit: not committed; proposed message given to user.

### 2026-11-11 — Claude — RF-03 — Done
- Did: steps 3–4. User: "yes accept every recommended choices" → A1–A5 a; U1 b
  (60 px); U2 c (set width after a browser layout test); U3 a; U4 a; U5 a.
  Recorded as dated user decisions in `AGENTS.md` (UX and assistant bullets) and
  in notes at the end of both source reviews; PROGRESS "Decisions still open" bullet
  replaced. No code change needed, so nothing added to the roadmap "Later" list.
- Files: `AGENTS.md`; `docs/reviews/2026-11-01-assistant-actions.md`;
  `docs/reviews/2026-11-03-ux-r24-handoff.md`; `DECISIONS_FOR_USER.md`;
  `docs/PROGRESS.md` (two hunks: decisions bullet, pointer); `docs/COMPLETED.md`
  (top RF-03 entry); this file.
- Checks: `git diff --stat` on my files; no tests run (docs only).
- Not done: nothing in RF-03. The U2 browser layout test is still open (not a gate).
- Waiting on user: nothing.
- Next step: RF-05 (repository cleanup), step 1 per TICKETS.md.
- Watch out: `frontend/BEARPLANS_UX_PLAN.md` and `BEARPLANS_UX_HANDOFF.md` still
  call these "proposed"; they were outside RF-03's file list, so not edited (AGENTS.md
  now takes precedence). PROGRESS.md and COMPLETED.md also carry Codex's uncommitted hunks.
- Commit: committed by user as `a55ccc3` (7 files; Codex's hunks left unstaged).
  `main` is 3 ahead of origin; not pushed.

### 2026-11-11 — Claude — RF-03 — Waiting on user
- Did: steps 1–2. Wrote `DECISIONS_FOR_USER.md`: 10 one-letter questions
  (A1–A5 = Assistant defaults 2–6, already built; U1–U5 = UX row height,
  wide-layout width, cross-month filing, Earlier unfinished, Figma font).
- Files: `docs/plans/refinement/DECISIONS_FOR_USER.md` (new); this file;
  `docs/PROGRESS.md` (refinement pointer only).
- Checks: read source passages (actions review "Decisions"; UX plan §2; UX
  handoff "Defaults/discrepancies"); `styles.css` rows are 60 px; no 1280 px
  breakpoint in code. No tests run (docs only).
- Not done: step 3 answers; step 4 recording (AGENTS.md/review notes, PROGRESS list).
- Waiting on user: answers to A1–A5, U1–U5 (asked in chat).
- Next step: record each answer in the sheet's Answers table, then step 4.
- Watch out: RF-02 entry said "not committed"; user committed `8acd618`, which
  also included Codex's PROGRESS/COMPLETED hunks linking two still-untracked
  reviews. `main` is 2 ahead of origin. Codex was active during this session
  (uncommitted): `TaskCaptureForm.tsx` + test, `taskCaptureRecovery.ts`, three
  reviews, a COMPLETED.md entry and a title-accessibility hunk in PROGRESS.md.
- Commit: not committed.

### 2026-11-11 — Claude — RF-02 — Done
- Did: steps 3–5. User: "We can wait for these all", then "yes accept them as
  unverified" → G-07–G-12 accepted as unverified (not passed, block nothing). User asked for a precise, detailed rule and
  delegated the refinement; added "Open gates and the limit on waiting work" to
  `AGENTS.md` (limit three; count, exceptions, override, add/close/defer). Added a
  GATES link in PROGRESS "Open follow-ups"; bullets kept (Codex edits that file).
- Files: `AGENTS.md`; `docs/GATES.md`; `docs/PROGRESS.md` (two hunks: link and
  pointer); `docs/COMPLETED.md` (top RF-02 entry); this file.
- Checks: relative links in GATES.md and the new AGENTS.md section resolve (see chat).
- Not done: nothing in RF-02.
- Waiting on user: nothing.
- Next step: RF-03 (decision sheet), step 1 per TICKETS.md.
- Watch out: limit is already exceeded (4 user-owned blocking gates); new builds
  wait until G-03 passes or the user overrides. Codex's uncommitted work: two
  reviews, `taskCaptureRecovery.ts` + test, hunks in PROGRESS.md and COMPLETED.md.
- Commit: not committed; proposed message given to user.

### 2026-11-11 — Claude — RF-02 — Waiting on user
- Did: steps 1–3. Wrote `docs/GATES.md`: 12 gates (3 block the trial, 3 block the
  alpha, 6 can wait) plus a "not gates" list; evidence links checked as tracked files.
- Files: `docs/GATES.md` (new); this file; `docs/PROGRESS.md` (pointer only).
- Checks: all 15 evidence paths → tracked in Git. No tests run (docs only).
- Not done: step 3 answers (defer G-07/G-11?), step 4 rule text in `AGENTS.md`,
  step 5 PROGRESS link.
- Waiting on user: which "can wait" gates to accept as unverified; the rule number
  and wording. Note 4 user-owned gates (G-03–G-06) block trial/alpha, so a limit of
  three would stop new builds today.
- Next step: record the user's answers in GATES.md, then steps 4–5.
- Watch out: previous entry said "not committed"; user committed it as `123e5f4`.
  `main` is 1 ahead of origin (was 54). `(1)` copies are git-ignored. Codex edited
  during this session (uncommitted): `frontend/src/taskCaptureRecovery.ts`, its test,
  `docs/COMPLETED.md`, a new storage-access review and a paragraph in `docs/PROGRESS.md`.
- Commit: not committed.

### 2026-11-11 — Claude — RF-01 — Done
- Did: step 6. User approved the proposed dates ("go ahead"); wrote them into the
  roadmap "Next" table: Nov 14 / Nov 16 / Nov 17–23 / Nov 24 (weekdays checked).
- Files: `BearPlans_Dated_Roadmap.md`; this file; `docs/PROGRESS.md` (pointer only);
  `docs/COMPLETED.md` (new top entry).
- Checks: link check → 34 relative link occurrences, all exist and are tracked.
- Not done: nothing in RF-01.
- Waiting on user: nothing.
- Next step: RF-02 (gate register and limit on waiting work), step 1 per TICKETS.md.
- Watch out: user committed RF-01 part 1 (`105928b`) and the plan files (`5687685`);
  tree was clean except the `(1)` copies at session start. Task-entry close target
  is Nov 14; RF-04 still waits on it.
- Commit: not committed; proposed message given to user.

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
