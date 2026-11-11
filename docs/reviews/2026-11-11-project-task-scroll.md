# Crowded project task scrolling — November 11, 2026

**Result: Pass with follow-ups.** Project task lists have a bounded scroll area and an accessible list name, following the [crowded Projects reference](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=82-6877). Task rows and edit forms remain mounted; page scrolling is not explicitly suppressed. No task records or completion rules changed. This does not implement the prototype drawer or planned-week Done hierarchy.

## Verification

On macOS Darwin arm64:

- `npm --prefix frontend test`: 191 passed.
- `npm --prefix frontend run build`: passed, including TypeScript checking; rerun after the final scroll-boundary CSS refinement.
- `BEARPLANS_E2E_CHANNEL=chrome BEARPLANS_EVIDENCE_DIR=/tmp/bearplans-project-scroll .venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox tests/test_project_list_scroll_browser.py tests/test_project_controls_browser.py tests/test_compact_project_tasks_browser.py tests/test_m1_journey_browser.py`: 10 passed before the final CSS refinement. Final focused scroll suite: 3 passed with the same command and `tests/test_project_list_scroll_browser.py`, evidence in `/tmp/bearplans-project-scroll-final`.
- The focused tests cover 15 tasks, long names, the last task, keyboard-opened editing, retained unsaved title after switching views, no horizontal overflow, and 375 dark, 640 light and 1440 dark. Inspected the 640 light screenshot. User review and VoiceOver remain untested.
