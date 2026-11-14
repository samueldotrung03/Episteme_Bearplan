# Atelier redesign — implementation plan

Written November 14, 2026. **Plan only: no application code has changed.**
Source: Figma file *BearPlans — Atelier redesign (Test 1)*, Screens page
(`Sxhit2hudslGGvwqkxpX8G`, node `1:5`). Status lives in
[docs/PROGRESS.md](../../../docs/PROGRESS.md), not here.

## What the Figma file contains

The Screens page has 13 sections, about 200 frames at 1440 px plus 1024/1920 reflow
references. The "dashboard" is **S1 Today** (ideal frame `18:5`, 19 state frames).
The other sections are S2 Week, S3 Projects, S4 Task editor, S5 Done,
S6 Track, S7 Close week, S8 Stats and goal editor, S9 Assistant chat history,
S10 Settings (Connections, Google, bCourses, Assistant, Data), S11 Sync change,
S12 Disconnect, S13 New from bCourses, and Local failures.

## Visual system to adopt (from Figma variables on `18:5`)

| Figma variable | Value | Current `styles.css` token |
| --- | --- | --- |
| `--color-canvas` | `#f3efe9` | `--bg` `#f6f4ef` |
| `--color-surface` / `-raised` / `-sunken` | `#fbf9f6` / `#ffffff` / `#eae4db` | `--surface` only |
| `--color-ink` / `-muted` / `-inverse` | `#2a2420` / `#6e645b` / `#fbf9f6` | `--text`, `--muted` |
| `--color-line` / `-strong` | ink at 10% / 18% | `--border` |
| `--color-accent` / `--color-on-accent` | `#2f6b4f` / `#fbf9f6` | same accent already |
| `--color-wood-100/200/400` | `#f1e6d6` / `#e3cfb3` / `#b98f63` | none (event chips, streak) |
| `--color-warning` | `#c98a1b` | none |
| Spacing 4/8/12/16/24/32/48; radius 8/16/pill; control 40/32 | | ad hoc values |
| Glass app bar: white 64% + 24 px blur | | solid header |

Dark-mode values are not in this frame; derive them and check contrast. **Font:**
Atelier uses Geist. On 2026-11-14 the user chose "Switch to Geist", replacing the
2026-11-11 system-font decision. Bundle Geist locally (offline app; no Google Fonts
request) with the system font as fallback.

## S1 Today: current app versus Atelier

| Element in Atelier | Today in the app | Work |
| --- | --- | --- |
| Glass app bar: Plan · Track · Stats · Assistant + settings icon | Also has bCourses and Google links | Move bCourses/Google into Settings (S10) and a Today banner (S13); frontend only |
| Header: "Today" + date, Today/Week segmented, Projects, + Add task | Separate Plan-views nav with Today/Week/Projects | Restyle; Add task needs a project picker because the capture form is project-scoped |
| Streak with seven week dots, minutes focused today | `DailyStreak` compact | Check whether the API exposes per-day results for the dots |
| "8 tasks · 3h 50m planned · your order" | "N unfinished · N complete" | Frontend sum of `estimate_minutes`; "your order" needs persisted within-day order (not built) |
| Calendar event chips strip | Events only in Week | Reuse Week's event data |
| One card of rows: checkbox, title, context, time, estimate; Start on the focused row | Rows with Start on every row | Restyle; `start_time` and `estimate_minutes` already exist |
| bCourses / "Changed in bCourses" badges | Not shown | Source badge is likely available; the change badge depends on S11 sync-change data |
| Completed · N disclosure | Exists | Restyle |
| Earlier unfinished · N | Not built | Domain/API work (accepted design, not implemented) |
| Keyboard hints: Enter, X, N, W, P | None | New shortcuts; must not fire while typing |
| Toasts with Undo (task deleted, import deleted) | No delete Undo on Today | Separate backend capability |

## Proposed slices (one active at a time)

1. **A0 Tokens and shell (frontend only).** Add the Atelier tokens alongside the
   old ones, map existing classes, glass app bar and four-item nav, Settings
   holding bCourses/Google. Light and dark. No API change.
2. **A1 Today dashboard (frontend only).** Header, summary row, event strip, task
   card, focused-row Start, Completed disclosure, keyboard hints and shortcuts,
   empty/loading/error/overflow/200%-zoom states matching S1 frames.
3. **A2 Today data gaps (backend + frontend, separate authorization).** Earlier
   unfinished, Add task with project choice, streak dots if missing, sync-change
   badge.
4. **A3+ Other screens** in the order Week → Projects/Task editor → Done →
   Track → Close week → Stats → Settings → Assistant, each restyling existing
   behavior first and listing its domain gaps separately.

Each slice follows AGENTS.md verification: `python3 tools/check.py`, browser
checks at 640, 800 and 1440 px in light and dark, a review in `docs/reviews/`,
and a new `docs/GATES.md` row for any user acceptance it leaves open.

## Before any slice starts

On November 14 there are **four** user-owned gates in the "block the trial" and
"block the alpha" tables (G-03, G-04, G-05, G-06), above the limit of three in
AGENTS.md. A0/A1 are new builds, so they need either one gate closed or deferred,
or the user's explicit override in chat (recorded in PROGRESS.md).
