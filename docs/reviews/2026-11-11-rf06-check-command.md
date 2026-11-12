# One command for every check (RF-06) — November 11, 2026

**Result: Pass.** `tools/check.py` runs frontend typecheck, frontend tests, frontend
build and backend tests, stops at the first failure, prints one line per step and
exits non-zero on failure. Both the fast and the full set pass. The full set first
failed on 4 real-browser add-task tests that were already failing before this ticket
(UX slice, Codex's area). A later rerun passed with Codex's then-uncommitted fix in
the tree (see the last table row). The user declined the optional pre-push hook and
GitHub Actions workflow on November 11 ("we already test in other part").

Setup: macOS Darwin arm64, Python 3.13.15 in a new `.venv` from
`requirements-dev.lock`, Node v24.21.0 with `npm ci`, a fresh clone at `763e266`.

| Run | Result | Time | Totals |
| --- | --- | --- | --- |
| `python3 tools/check.py --fast` | exit 0 | 99.8 s | frontend 213 passed; backend 1079 passed, 1 skipped, 63 deselected (e2e) |
| `python3 tools/check.py` | exit 1 at backend tests | 329.0 s | frontend 213 passed; backend **4 failed**, 1138 passed, 1 skipped |
| `--fast` with a deliberate failing test (`tests/test_zz_rf06_canary.py`, removed afterward) | exit 1 | 96.2 s | backend 1 failed, named in the output |
| `python3 tools/check.py` rerun, with Codex's uncommitted edits to `frontend/src/TaskCaptureForm.tsx`, `styles.css` and the two failing test files | exit 0 | 296.6 s | frontend 213 passed; backend 1142 passed, 1 skipped |

The 4 full-run failures, the same ones recorded in the RF-05 handoff:

- `tests/test_add_task_disclosure_browser.py::test_add_task_retry_cancel_and_focus[375-dark]`, `[640-light]`, `[1440-dark]`: the "Could not save task" alert text was not found.
- `tests/test_e2e_browser.py::test_long_text_layout_and_keyboard_creation`: the field was expected to be empty after save.

**Data safety.** The script sets `BEARPLANS_DATA_DIR` to a new temporary folder and
`BEARPLANS_SECRETS_FILE` to a non-existent file in it. This differs from the
ticket's "empty value": `backend/platform/secrets.py` treats an empty value as
unset and falls back to the data folder. `find ~/Library/Application\ Support/BearPlans -newermt "2026-11-11 21:20"`
returned nothing after the runs. Reads cannot be ruled out this way. They are
prevented by the environment variables, and the tests also set their own.

**Notes.** The first `--fast` attempt right after `npm ci` failed with vitest
"Cannot find package" errors. Plain `npm test` and every later run passed, so this
was treated as a transient install-timing issue (not verified further). No dependency
was added. Linting (`ruff`, `eslint`) is a follow-up, because it is a dependency change.
