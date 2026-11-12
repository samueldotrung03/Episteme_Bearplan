# Task-entry presentation matrix — November 11, 2026

**Pass for G-13 on the current inline form.** On macOS, headless Chrome and a
schema-24 local service with disposable data exercised light and dark themes at
640, 800 and 1440 px. At each size, the test opened the project form with Enter,
typed a synthetic title, tabbed to Add task, saved with Enter and verified the
task appeared and focus returned to Add task. Inputs and buttons fit horizontally;
vertical scrolling is required. Screenshots of all six combinations were
inspected for field labels, controls and visible submit focus.

Command: `PYTHONPATH=. .venv/bin/python /private/tmp/bearplans-dialog-matrix-check.py`
(6 combinations passed). The focused failure/retry browser checks and inspected
error screenshots at 375 dark, 640 light and 1440 dark are recorded in the
[alignment review](2026-11-11-task-entry-figma-alignment.md); real quota failure
is in the [quota review](2026-11-11-task-capture-real-quota.md). These checks do
not establish screen-reader operation, every error state, zoom reflow or acceptance
of the Figma modal, which is not yet implemented. A later modal change requires
fresh browser verification.
