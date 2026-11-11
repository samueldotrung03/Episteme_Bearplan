# On-demand project task entry — November 11, 2026

**Pass with follow-ups.** On macOS Darwin arm64, Projects shows a compact + Add task control until opened. The existing fields and validation remain; errors retain input for retry, Cancel discards that draft and returns focus, and Cancel is disabled during a pending save. The form stays open and clears after success for consecutive entry. Separate drafts remain in memory across project and Plan-view changes, including Settings navigation; they are not durable across app reload. No API, database, scheduling or timer rules changed.

References: [Projects](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=5-4847), [task details](https://www.figma.com/design/jobFe4sXDot7BKsej0arNB?node-id=5-5491). This scoped inline disclosure is not yet the Figma modal; planned-day entry and atomic task/placement Save require later domain and UI work.

Checks: `npm --prefix frontend test` (189 passed); `npm --prefix frontend run build` (typecheck and build passed). Guarded disposable Chrome run of e2e, Today, M1, timer and Settings: 23 passed, one failed due to the preceding completed-row change hiding Edit. Updated the affected journey to reopen before editing/removing and reran it: 1 passed. New failure/retry/cancel/keyboard/layout browser checks: 3 passed at 375 dark, 640 light and 1440 dark; inspected 640 light screenshot. The affected fake-Google browser journey also passed. No live provider or personal data used.

Manual VoiceOver, modal fidelity, combined task/planned-day save, broader UX acceptance and release/hardware gates remain open.
