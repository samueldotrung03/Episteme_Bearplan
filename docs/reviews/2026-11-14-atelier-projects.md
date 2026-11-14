# Atelier redesign A4: Projects + Task editor — review

November 14, 2026. Source design: Figma *BearPlans — Atelier redesign (Test 1)*,
S3 Projects (`18:191` ideal, `141:30701` project menu) and S4 Task editor
(`41:3809` edit), file `Sxhit2hudslGGvwqkxpX8G`.
[Plan](../../frontend/plans/atelier-redesign/PLAN.md). Started on the user's
override ("Override, start Projects", Nov 14) with six user-owned gates open
(G-14, G-15, G-16, G-04, G-05, G-06). Frontend only; no API, schema or saved-data
change.

**Scope decision (user, Nov 14):** "Restyle in place first". Projects stays its
own plan view instead of Figma's glass side panel over Today/Week; the panel move
is a later, separate step.

## What changed

- **Header.** "Projects" is a 28 px page title in the same 880 px column as Today
  and Week, with the shared Today/Week, Projects controls beside it. The
  "Projects" region is still labelled by that heading.
- **Project picker.** Project chips are now small pill tabs on a sunken track
  (selected = ink, never the accent), followed on the same row by a quiet
  "Rename" and a secondary "Add project" pill with a plus icon. Long names
  truncate in the pill; the full name stays in the project heading. Accessible
  names are unchanged ("Rename “…”", "+ Add project").
- **Project heading.** Project name in 20 px medium with "N of M work items
  complete" below and an ink "Add task" pill on the right ("+ Add task" /
  "Continue task draft" for assistive technology, as before).
- **Task list.** One surface card like Today's: 56 px rows, round 20 px checkbox
  in a 32 px target (ink when checked), 16 px title, 13 px muted meta joined by
  " · ". Parent tasks use a 14 px medium title and a dashed checkbox (derived
  completion); subtasks are indented 32 px with no rule. Row actions are quiet
  text pills ("Edit", "Add subtask") plus the existing "Start tracking". Planning
  disclosures use ink text. The list still scrolls inside its card (60 vh).
- **Task editor (inline edit, subtask, rename/add project forms).** Raised card,
  13 px medium labels, 40 px fields with a 2 px ink focus ring, actions on the
  right: secondary "Cancel", accent "Save changes"; "Remove subtask" is danger
  text on the left, with the confirmation in a sunken box.
- **New task dialog.** 24 px radius raised card on a warm 28 % scrim, 20 px
  "New task" title, the same fields, accent "Add task", secondary "Cancel" and a
  quiet "Keep draft while this page is open" on the left.

## Deliberate differences from the frames

- Not a side panel (scope decision above); no "P close · N add task here" footer.
- Project dropdown and ⋯ menu (Rename / Delete project…) are shown as the pill
  strip and visible Rename/Add project controls, so every existing control and
  test keeps working with no extra click.
- Not built (need behaviour or data): Active/Done filter, "Completed · N" per
  parent, "Planned Fri, Oct 30" / "50 min left" row context, project delete,
  course projects and module sections, Source/Sync marks, Undo after a subtask
  delete, editor fields for Project / Day / Start in one dialog, Ctrl+Enter to save.

## Checks (macOS, Nov 14)

- `npx vitest run`: 219 passed. No test changes were needed.
- First full check failed `test_long_text_layout_and_keyboard_creation`: a
  100-character project name overflowed at 375 px. Fixed by letting the pill
  shrink (`.project-list > li { min-width: 0 }`); rechecked at 1280 and 375.
- Full `python3 tools/check.py`: all 4 steps passed (typecheck; 219 frontend
  tests; build; 1180 backend/browser tests passed, 1 skipped) in 318 s.
- Screenshots on disposable data (installed Chrome): 1440 light and dark, 800
  light, 640 dark, the edit form, the New task dialog and long names at 375; no
  horizontal overflow. Evidence: [screens](evidence/2026-11-14-atelier-projects/).

## Not verified

- Screen-reader operation and 200 % zoom.
- User acceptance: open as gate G-17.
