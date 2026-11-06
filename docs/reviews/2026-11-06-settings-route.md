# APP-C05.1 — Settings route and work context

**Pass with follow-ups.** Verified on macOS 26.6.2 arm64 with Node 24.21.0
and headless Chrome 156.0.8078.74. Scope is UI-10 and DATA-05 navigation.
APP-C05.2, APP-C05.3 and the broader integration gates remain open.

- The shared Settings link is available from Plan, Track, Stats, Assistant
  and both existing provider screens. A fresh launch still opens Plan on
  Today. A direct Settings visit has Plan as its fallback.
- Work components stay mounted. The Settings history entry remembers the
  originating screen and window scroll offset. Back to work uses browser
  history to restore that entry, and browser Back/Forward also works. Entering
  Settings focuses its heading. Returning focuses the shared entry or Track's
  existing screen heading, without scrolling the focused element into view.
- The Connections section links to the existing bCourses and Google screens.
  This is the application routing slice and uses the existing app shell and
  colors. Provider panels, status details and setup dialogs are separate slices.
- Opening and closing Settings does not write task, placement, timer or reward
  records. The existing live countdown remains available during the visit.

## Checks

- `npm --prefix frontend test` — 177 passed in 15 files.
- `npm --prefix frontend run typecheck` — passed.
- `npm --prefix frontend run build -- --outDir "$bp_build_dir"` — passed with a
  fresh disposable output directory.
- `BEARPLANS_E2E_CHANNEL=chrome`, with `backend.platform.paths.FRONTEND_DIST`
  pointed at that build, pytest `-q -p no:cacheprovider -p tests.connections_sandbox
  tests/test_settings_browser.py tests/test_google_browser.py` — 2 passed.
  The first run passed the main navigation and Google checks, then hit a
  Playwright fixture error opening a second tab. The corrected run passed.
- Chrome checked the selected week, day and project, draft retention, exact
  scroll restoration, keyboard activation and focus, history, direct entry,
  provider links, an unchanged running session ID and exact paused session
  state. Layout assertions covered Light at 640px and Dark at 320, 640, 800
  and 1440px. Inspected the 320px Dark screenshot for wrapping and controls.
  The guarded fixture uses disposable databases and blocks external provider
  HTTP. Google regression uses fake clients.
- Needs review navigation, actual 200% browser zoom, assistive technology,
  native wrapper and live provider verification remain pending. No backend or
  migration changed in this slice.
