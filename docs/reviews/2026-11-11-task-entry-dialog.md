# Task-entry dialog — November 11, 2026

**Result: In progress; user acceptance remains open.** On macOS, the project
task-entry form opens in a native modal dialog based on the
[Figma task-details frame](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=5-5491).
Save and recovery retain their existing atomic capture and replay behavior. A
draft can be put aside with Escape or the keep-draft control, then resumed in
the same page; ordinary unsaved drafts do not survive closing or reloading it.
Pending save receipts continue to use the existing persistent recovery path.
No schema or domain behavior changed.

The focused React tests passed 50 tests and typecheck passed. The browser test
in `tests/test_add_task_disclosure_browser.py` passed nine cases with a
disposable service on macOS Chrome: six width/theme combinations (640, 800,
1440 pixels, light and dark) checked focus containment, Escape, retained draft,
reopen and Cancel; three existing cases checked a failed save and recovery at
375 dark, 640 light and 1440 dark, including putting the pending save aside and
reopening it. Visually inspected normal states at 640 light and 1440 dark and
the 375 dark error state. An initial sandboxed browser run skipped nine
cases because Chrome could not start; the unrestricted run passed all nine.
The user has not accepted this implementation, and screen-reader operation and
the remaining redesign screens are not verified by these tests.

The first full `python3 tools/check.py` run passed typecheck, 213 frontend tests
and build, then failed five browser cases (1143 passed, one skipped). Their old
paths attempted background navigation while the new dialog was open. Updated
the Settings, Google and Today journeys to keep and resume the draft; 13 of the
14 focused cases passed on the first rerun. The Settings case also needed
scrollable space because closing the dialog shortened the page; it passed after
adding that test setup. A subsequent unrestricted `python3 tools/check.py`
passed typecheck, 213 frontend tests, build, and 1148 backend/browser tests
with one skipped. That run started before the final in-flight Escape guard.
For that guard, the final tree passed typecheck, 43 App tests, a fresh production
build and all 10 task-dialog browser cases, including a real Chrome in-flight
save. The full suite was not rerun after that last two-line guard.
