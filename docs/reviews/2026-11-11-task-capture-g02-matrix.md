# Task entry keyboard and theme matrix — November 11, 2026

**Result: Pass for G-02; accessibility follow-ups remain.** On macOS Darwin
arm64, Playwright drove installed Chrome headlessly against the production
interface at commit `400bdfe` and a schema-24 loopback service using disposable
data in `/private/tmp/bearplans-g02-20261111`. The service was stopped afterward.

At each combination of light and dark appearance and 640×900, 800×900 and
1440×900 viewport, the check selected Projects, focused Add task, opened it
with Enter, typed a synthetic title, tabbed through the form to Add task, and
saved with Enter. The saved task appeared and focus returned to Add task in all
six cases. Native date fields have multiple Tab stops. Selection of Projects
used a click and initial focus was set programmatically; the form journey itself
used keyboard events. Each form control's horizontal bounds and document width
fit the viewport. Screenshots of all six form states were inspected: labels,
controls and the submit focus ring were visible in both themes. Vertical scroll
was needed at compact sizes.

Command: `.venv/bin/python /private/tmp/bearplans-g02-check.py` (six combinations
passed; script and screenshots are disposable local evidence). This was a bounded
normal-save check, combined with the earlier [keyboard](2026-11-11-task-capture-keyboard-order.md),
[dark recovery](2026-11-11-task-capture-dark-mode.md) and
[cross-tab focus](2026-11-11-task-capture-cross-tab-focus.md) reviews. It did not
exercise date entry, every error state, screen readers, zoom, separate-window
focus or a full contrast audit. G-01 storage/lock failure and G-03 user acceptance
remain open; this check does not establish full redesign acceptance.
