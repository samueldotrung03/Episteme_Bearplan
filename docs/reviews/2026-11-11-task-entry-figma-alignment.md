# Task-entry Figma alignment — November 11, 2026

**Result: In progress; visual and user acceptance remain open.** On macOS,
compared the task-details frame [5:5491](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=5-5491)
with the current project form. Added a New task heading, adjusted its surface,
spacing and input sizing, and moved the deadline/planned-day explanation below
the notes. The form is still inline; the designed modal, its focus behavior and
the other redesign screens are not implemented by this change.

`npm --prefix frontend test`: 213 passed. `npm --prefix frontend run build`:
passed including typecheck. The first full `python3 tools/check.py` run in the
sandbox failed because local service tests were denied permissions. An unrestricted
run passed the frontend steps and reported 4 browser-test failures, 1138 passed
and 1 skipped. Three old tests intercepted `/api/tasks` instead of the new atomic
capture endpoint; the fourth expected the form to stay open after a successful
save. Updated those checks to cover the capture endpoint, status check and focus
return. The four affected browser cases passed with
`.venv/bin/python -m pytest tests/test_add_task_disclosure_browser.py tests/test_e2e_browser.py::test_long_text_layout_and_keyboard_creation -q`.

Inspected the error-state screenshots at 375 px dark, 640 px light and 1440 px dark from the
focused run; these do not cover the full width/theme matrix. The failed-save
case used a simulated response, not a real browser storage or lock fault. G-01,
G-03 and G-13 remain open. After scoping the presentation styles to the capture
form, unrestricted `python3 tools/check.py` passed all four steps: frontend
typecheck, 213 frontend tests, frontend build, and 1142 backend/browser tests
with 1 skipped. The full run used disposable data on macOS.
