# Atelier redesign A0 + A1: tokens, app bar and Today — review

November 14, 2026. Source design: Figma *BearPlans — Atelier redesign (Test 1)*,
Screens page, frame `18:5` "S1 Today / ideal" (file `Sxhit2hudslGGvwqkxpX8G`).
[Plan](../../frontend/plans/atelier-redesign/PLAN.md). Started after G-03 passed
(three user-owned gates open). Frontend only; no API, schema or saved-data change.

## What changed

- **Tokens (A0).** `styles.css` defines the Atelier colour, spacing, radius and
  control-size variables from the Figma variables, with derived dark values.
  The older names (`--bg`, `--surface`, `--text`, ...) are now aliases, so the
  screens not yet redesigned (Week, Projects, Track, Stats, Assistant, Settings)
  take the new palette without layout changes. Focus rings use ink (design rule).
- **Font.** Geist (variable) is bundled through `@fontsource-variable/geist`
  5.3.0 and served locally from `dist/assets`; no network font request. System
  fonts remain the fallback. User decision Nov 14: "Switch to Geist".
- **App bar (A0).** Sticky glass bar, tree brand icon, pill destinations Plan ·
  Track · Stats · Assistant (selected = ink pill), settings icon button. The
  bCourses and Google links left the top bar; both screens are still reached from
  Settings ("Review assignments", "Open Google") and by `#bcourses` / `#google`,
  and Settings shows as current while either is open.
- **Plan header (A1).** Title "Today" + date, Today/Week segmented control,
  Projects and Add task pill buttons. "Plan views" navigation is kept for
  accessibility and tests. Add task opens the existing task form for the selected
  project (in Projects); with no project selected it shows Projects and focuses
  Add project. It is hidden in the Projects view, which has its own add control.
- **Today (A1).** Summary row with the quiet streak (label, "N of 60 min focused
  today", seven day dots: ink = qualified, wood = missed, ring = today) and
  "N unfinished · N complete · Xh Ym planned"; calendar events for today as wood
  strips; one task card with round checkboxes, title and context, start time,
  estimate and Start; the focused row has an ink border and the accent Start,
  other rows show Start on hover or keyboard focus; Completed disclosure with
  chevron and compact struck-through rows; keyboard hint line.
- **Keyboard.** Enter starts the focused task, X completes it, ↑/↓ (or J/K)
  choose a row, N new task, W week, P projects. Ignored while typing, while any
  button/link has focus, with modifier keys, when Today is hidden or a dialog is
  open.
- **Icons.** Downloaded from the Figma frame into `frontend/src/assets/atelier/`
  (tree, settings, folder, plus, play, chevron-right, alert, link, three dots)
  and drawn as CSS masks so they follow light/dark text colour. Alert, link and
  dot files are stored for later slices.

## Deliberate differences from the frame

- Rows have a 60 px minimum (user decision Nov 11) instead of Figma's 56 px.
- "your order" is omitted from the summary: within-day order is not persisted.
- Not built (need data/backend, slice A2): Earlier unfinished, the bCourses
  Source mark and "Changed in bCourses" Sync mark, Undo after delete, choosing a
  project inside Add task.
- An extra "↑↓ choose" hint documents the row-selection keys.

## Checks (Linux cloud container, not macOS)

- `npm run typecheck` passed; `npx vitest run`: 217 tests passed (3 new Today
  tests: summary/events/start time, keyboard shortcuts, shortcut guards; updated
  streak copy); `npm run build` passed.
- Browser (Playwright Chromium, disposable schema-25 data, port 18994): Today at
  1440 light, 1440 dark and 640 light; ArrowDown moved focus and the Completed
  disclosure expanded. Evidence: [screens](evidence/2026-11-14-atelier-today/).
- Browser tests that clicked the removed bCourses/Google top-bar links now set
  the same hash the Settings links use (`tests/test_bcourses_browser.py`,
  `tests/test_google_browser.py`).
- Full `python3 tools/check.py`: exit 0 (typecheck, 217 frontend tests, build,
  1175 backend/browser tests, 1 skipped). `tests/test_today_browser.py` was
  updated for the new top bar, the icon-less streak and Start appearing on hover.

## Not verified

- Screen-reader operation, 200 % zoom, and the Today empty/loading/error states
  against their Figma frames.
- Contrast of the derived dark palette was judged visually, not measured.
- Other screens were not reviewed for regressions beyond the automated tests.
- User acceptance: open as gate G-14.
