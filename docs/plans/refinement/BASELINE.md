# Baseline scorecard — November 11, 2026

Two evaluations on the same day. The second followed the user's cut of
`docs/PROGRESS.md` and the first UX redesign commits. RF-08 re-scores these same
aspects.

| # | Aspect | Morning | After update | Why it moved |
| --- | --- | --- | --- | --- |
| 1 | Architecture and system design | 88 | 88 | — |
| 2 | Test and verification depth | 90 | 91 | Nine new browser test files with the UX work |
| 3 | Data safety and privacy | 87 | 87 | — |
| 4 | Implementation quality | 82 | 82 | Still no linter; `App.tsx` still growing |
| 5 | Requirements and product rules | 82 | 82 | Same decisions still open |
| 6 | Evidence and review discipline | 85 | 85 | — |
| 7 | Agent handoff system | 78 | 84 | One active slice with one named next step |
| 8 | Documentation usability | 62 | 68 | Progress file is readable in two minutes |
| 9 | Progress tracking | 60 | 76 | 605 lines cut to 83; but the milestone table now lives only in Git history |
| 10 | Roadmap and scheduling | 40 | 40 | Roadmap untouched since November 3 |
| 11 | Scope and sequencing control | 48 | 46 | Twenty more feature commits before the core trial |
| 12 | Release readiness and gate closure | 45 | 43 | Trial candidate is now eight schema versions behind |
| 13 | Repo hygiene and automation | 45 | 42 | Unpushed commits rose from 35 to 54; duplicates remain |
| | **Overall** | **70** | **72** | Execution about 86, trackability about 62 |

## Evidence used

- Backend: `.venv/bin/python -m pytest` → 1,102 passed, 1 skipped (Windows-only),
  at commit `77f7ebf`, macOS. Not re-run on later commits.
- Frontend: `npm --prefix frontend test` → 207 passed on the working tree after
  `9d2aa32`; typecheck clean at `77f7ebf`.
- No SQL statements in `backend/routes/`; 24 migrations; service binds loopback
  with Host and Origin checks in `backend/app.py`.
- No tracked credential files; `.secrets/`, `.evidence/`, `.venv/` ignored.
- No tags, no CI, no pre-commit hook, no linter configuration.
- 29 untracked `(1)` paths, about 120 MB.
- Roadmap status line dated October 23; "Assistant actions" row marked not
  started; last commit to the file November 3.
- Core trial: candidate `bearplans-local-core-2026-11-01`, no Day 1 reported.
- The interface itself was not inspected in a browser for this scorecard; the
  UX assessment rests on commits, tests and review records.

## Scoring rules for the re-evaluation

Score what the tree and records show, not what a summary claims. A document
that contradicts the tree lowers the documentation and tracking scores. A gate
that is "pending the user" counts as open regardless of how long it has waited.
