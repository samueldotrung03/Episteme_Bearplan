# BearPlans backend guidance

Applies throughout `backend/`. Read and retain the shared rules in
[root AGENTS.md](../AGENTS.md); this guide adds backend navigation and the backend
lane's limits without replacing the product, architecture or data-safety rules
there. Explicit user instructions and current authorization remain authoritative.

## Start with the current checkout

- Read [shared progress](../docs/PROGRESS.md), inspect Git status, recent commits,
  the full relevant diff and untracked files before changing work in progress.
- Run `git worktree list` and `git branch --show-current`. When two agents are
  working, the backend lane works in its own worktree folder on its own branch,
  never in the main folder. See "Parallel work" in the root guide.

## Find the relevant material

| Area | Entry point |
| --- | --- |
| Validation, business and completion rules | `domain/` |
| HTTP routes and app setup | `routes/`, `app.py` |
| Database, schema and migrations | `storage/db.py`, `storage/schema.py`, `storage/migrations/` |
| Paths, secrets, bCourses, Google, Ollama | `platform/` |
| Backups | `backup.py`, `domain/backups.py` |
| Backend and API tests | `../tests/` (see [tests/AGENTS.md](../tests/AGENTS.md)) |
| Assistant write actions | [assistant actions skill](../.agents/skills/bearplans-assistant-actions/SKILL.md) |
| Which document answers which question | [documentation map](../docs/README.md) |

## Backend lane limits (when a frontend agent is also working)

- Edit `backend/`, `tests/` except `tests/test_*_browser.py`, `tools/`,
  `pyproject.toml` and the Python lock files. Do not edit `frontend/`.
- Only this lane adds migrations. Before adding one, confirm the next free number
  on `main` as well as on the branch.
- For any route the interface will call, record the method, path, request,
  response and error codes in the slice's review file before the frontend lane
  builds against it. Keep existing responses compatible unless the change is
  agreed there; the frontend lane owns `frontend/src/api.ts`.
- If a backend change breaks a browser test, do not edit the test. Record the
  failing test and the reason in the review file for the frontend lane.
- Do not edit `docs/PROGRESS.md`, `docs/COMPLETED.md`, `docs/GATES.md` or the root
  guide on a lane branch. Put the handoff in `docs/reviews/YYYY-MM-DD-<feature>.md`:
  state, commands and results, failures and skips, open checks, proposed gate rows
  without IDs and the next concrete step.

## Commands

Run these from the root of the worktree you are in, using that worktree's `.venv`.

```sh
.venv/bin/python -m pytest
.venv/bin/python -m pytest tests/test_tasks.py
python3 tools/check.py --fast
python3 tools/check.py
```

The full `tools/check.py` run is required before a handoff or merge. Schema
changes also need the upgrade, rollback/retry and restart checks in the root guide.
