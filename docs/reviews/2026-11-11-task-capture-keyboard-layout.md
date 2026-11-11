# Task capture keyboard and layout check — November 11, 2026

**Result: Pass with follow-ups; task-entry acceptance remains open.** Tested on macOS Darwin arm64 in the in-app browser against a schema-24 loopback service and disposable data at `/private/tmp/bearplans-ux-keyboard-20261111`; the service was stopped afterward. No personal data was used.

Enter on Add task opened the form and focused Title. Keyboard entry and Enter on Cancel closed it and returned focus to Add task. Before the fix, successful Save removed the focused button and left focus on the document body. The fix returns focus to Add task when the same project is still selected; keyboard Save in the rebuilt running app showed the saved task and focused Add task. An automated regression covers this behavior. Native date controls have segmented Tab behavior; this check did not establish a complete browser or assistive-technology focus audit.

With light appearance and the form open, browser viewport overrides reported 640×800, 800×900 and 1440×900. DOM measurements placed each form input and action within the viewport horizontally, with document scroll width no greater than viewport width. Screenshots at 640 and 1440 showed the form and visible focus ring; vertical scrolling was necessary. These checks do not establish full-screen responsive acceptance, dark-mode contrast, enlarged text or error-state layout.

`npm --prefix frontend test` passed 208 tests in 19 files. The first `npm --prefix frontend run build` failed because a new test used an unsupported Testing Library option; after correcting the selector, the build and typecheck passed. User acceptance, real separate-window and storage/lock failure checks, dark theme and broader keyboard/accessibility checks remain open.
