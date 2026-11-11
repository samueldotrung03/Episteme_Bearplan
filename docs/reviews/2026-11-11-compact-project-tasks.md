# Compact completed project tasks — November 11, 2026

**Result: Pass with follow-ups.** On macOS Darwin arm64, completed project leaves show a checked checkbox and muted struck-through title. Notes, dates, planning and secondary actions return after a successful reopen; failures retain the checked row and display the error. Parent containers retain progress and their derived completion. Existing open edit forms are not discarded. Reopening is required before editing or removing a completed subtask. No storage or timer rules were changed.

Design reference: [Projects](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=5-4847) and the accepted compact completion specification. Existing task styles are reused; no assets added. The present project view is not yet the prototype drawer, and the Done hierarchy and weekly redesign remain open.

Checks: `npm --prefix frontend test` (188 passed); `npm --prefix frontend run build` (typecheck and build passed); disposable Chrome `tests/test_timer_eligibility_browser.py` (1 passed) and `tests/test_compact_project_tasks_browser.py` (3 passed at 375 dark, 640 light, 1440 dark; keyboard focus and no horizontal overflow). Reviewed the 640 light screenshot. First frontend run revealed four obsolete assertions expecting a disabled Start control, updated to reflect its removal. Initial build exposed an existing unsupported test query option, corrected.

Manual VoiceOver, full app redesign acceptance and hardware/release gates remain open. The browser fixture simulates only local data; real providers were not used.
