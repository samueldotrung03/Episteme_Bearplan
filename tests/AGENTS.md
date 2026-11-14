# BearPlans tests guidance

Applies throughout `tests/`. The shared rules are in [root AGENTS.md](../AGENTS.md)
(see "Verification, reviews and handoff" and "Parallel work").

| Files | What they test | Lane that edits them |
| --- | --- | --- |
| `test_*_browser.py` (marked `e2e`) | The interface in a real browser | Frontend |
| Other `test_*.py` | Domain rules, API, storage, restart and recovery | Backend |
| `conftest.py`, `connections_sandbox.py`, `fixtures/` | Shared support | Backend; tell the frontend lane before changing what browser tests rely on |

- Tests use disposable databases, a free port and an empty secrets file. Never
  point a test at real user data or real provider credentials.
- `python3 tools/check.py --fast` skips the browser tests; the full run includes
  them and is required before a handoff or merge.
- When only one agent is working, it may edit any test file.
