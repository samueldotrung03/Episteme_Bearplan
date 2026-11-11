# Decisions waiting on you

Created 2026-11-11 for refinement ticket RF-03 ("decision sheet for the user").
Ten choices have waited since early November. Each one below is a question you
can answer with one letter. A **recommended** choice is only a suggestion: nothing
here counts as decided until you answer it in the chat, and the answer is then
recorded where the rule lives.

How to answer: reply with a list such as `A1 a, A2 a, A3 b, U1 a …`. You can
answer some now and leave the rest open; unanswered items stay listed in
`docs/PROGRESS.md`.

Two groups:

- **A1–A5: the Assistant.** The Assistant is the chat panel that can create,
  change and complete tasks and start timers after you press **Apply**. These
  five rules are already built into the app as working defaults
  (`backend/domain/assistant_actions.py`), so "keep" costs nothing and "change"
  means a later code change. A1–A5 are defaults 2–6 in the
  [actions review](../../reviews/2026-11-01-assistant-actions.md#decisions)
  (default 1, "every action needs Apply", you already confirmed).
- **U1–U5: screen design.** These came from the redesign plan and the Figma
  mock-ups. Most are not built yet, so changing them now is cheap.

| # | Question (short) | Recommended |
| --- | --- | --- |
| A1 | Undo of an Assistant-created task deletes it only if unused | a (keep) |
| A2 | Undo of "mark complete" restores the exact old completion time | a (keep) |
| A3 | Timer actions have no Undo | a (keep) |
| A4 | One change per request; at most 4 follow-up questions | a (keep) |
| A5 | The server re-checks every proposal before Apply | a (keep) |
| U1 | Minimum height of a task row | b (60 px, as built) |
| U2 | Window width where the wide layout starts | c (decide after browser test) |
| U3 | Which month a week that spans two months is filed under | a (Monday's month) |
| U4 | What the "Earlier unfinished" list on Today shows | a (as proposed) |
| U5 | Font used in the Figma mock-ups only | a (Inter, Figma only) |

---

## A1 — Undoing a task the Assistant created

**Question.** When you press Undo on a task the Assistant just created, should
Undo delete the task only if you have not used it yet?

"Used" means anything happened to it after creation: a timer, a plan date, a
subtask, a completion, an edit.

- **a — Delete only while unused (current behavior).** Example: you ask "add
  Read chapter 4", Apply, then Undo → the task disappears. If you had already
  started a timer on it, Undo is refused with a message and the task stays.
- **b — Always delete, even after use.** Undo would also have to throw away
  timer history or plans attached to it.

**Recommended: a.** It never destroys time you tracked. The app has no general
"delete task" feature yet, so b would add one by the back door.
**Cost to change later:** moderate code change plus new tests.

## A2 — Undoing "mark complete"

**Question.** When you undo a completion change, should the task get back its
exact previous completion time?

- **a — Restore the exact previous time (current behavior).** Example: a task
  completed Monday 9:14, you ask the Assistant to mark it incomplete, then Undo →
  it is complete again at Monday 9:14, not "now".
- **b — Use the time of the Undo.** It would show as completed "now".

**Recommended: a.** Done lists and weekly history stay truthful.
**Cost to change later:** small code change.

## A3 — No Undo for timer actions

**Question.** Should starting, pausing or finishing a timer through the
Assistant have no Undo button, leaving the Track screen as the place to fix timers?

- **a — No Undo for timers (current behavior).** Example: "start a timer for
  Essay" → Apply → the timer runs; to stop it, use Track. Pausing an already
  paused timer does nothing.
- **b — Add Undo for timers.** This needs new rules for tracked minutes and
  rewards (for example, whether undoing a finish takes back earned points).

**Recommended: a.** Timer time and rewards have strict rules today; Undo would
need its own design.
**Cost to change later:** large; it is a new feature, so it would go to the
roadmap's "Later" list.

## A4 — One change per request, limited follow-up questions

**Question.** Should the Assistant handle one change per request and give up
after four follow-up questions, asking you to start again?

- **a — One change, at most 4 questions (current behavior).** Example: "add
  Essay and complete Reading" → the Assistant replies that it does one change at
  a time and asks which first. If it still lacks information after four
  questions (such as which of two projects you mean), it asks you to rephrase.
- **b — Allow several changes per request.** Each would still need its own Apply.
- **c — Keep one change, but a different question limit.** Tell me the number.

**Recommended: a.** One Apply per change keeps Undo simple and mistakes small.
**Cost to change later:** b is a large change; c is a one-line change plus tests.

## A5 — The server re-checks every proposal

**Question.** Should the app keep treating the Assistant's proposal as untrusted
and re-check it fully on the server when you press Apply?

- **a — Re-check everything (current behavior).** Example: the Assistant
  proposes "move Essay to Thursday"; before you press Apply you edit Essay by
  hand; Apply is then refused as out of date and you are asked to review again.
- **b — Trust the proposal as shown.** Slightly faster, but a stale proposal
  could overwrite your manual edit.

**Recommended: a.** It gives the Assistant the same checks as your own clicks.
**Cost to change later:** b would be a risky change; not advised.

## U1 — Minimum height of a task row

**Question.** What should the minimum height of an active task row be?

- **a — 64 px**, as the original redesign plan proposed (slightly roomier).
- **b — 60 px**, close to what is built now (the app's Today rows use 60 px; the
  reviewed Figma rows measured 59 px).
- **c — Decide later**, after reviewing a crowded Today list in the real app.

**Recommended: b.** It matches what you have already used, and long titles can
still grow taller.
**Cost to change later:** small style change.

## U2 — Window width for the wide layout

**Question.** At what window width should the app switch to the wide layout
(projects beside the work, seven-column week)?

Below that width, projects open in a drawer and Week shows one selected day.

- **a — 1280 px**, as the redesign plan proposed.
- **b — Another number** you choose.
- **c — Decide after a browser test** shows how much room projects, seven
  columns, long titles and buttons really need.

**Recommended: c.** The Figma comparison at 1279 and 1280 px both used the
narrow layout, so the number is not yet backed by a test.
**Cost to change later:** small once the wide layout exists; it is not built yet.

## U3 — Filing a week that spans two months

**Question.** In the Done history, which month should a week that crosses a
month boundary be listed under?

- **a — The month of its Monday.** Example: Oct 26–Nov 1 is listed under
  **October**, with the full date range shown.
- **b — The month of its Sunday.** The same week is listed under **November**.
- **c — Under both months.**

**Recommended: a.** Each week appears once, and weeks start on Monday in this app.
**Cost to change later:** small; this view is not built yet.

## U4 — What "Earlier unfinished" shows on Today

**Question.** Should Today's collapsed "Earlier unfinished" section show
unfinished tasks that were planned for a past day and are not planned for today
or any future day?

Details of the proposal: each task appears once; tasks in an archived (ended)
week still count; opening the section never moves or reschedules anything.

- **a — Yes, as proposed.** Example: "Essay outline" was planned for last
  Tuesday, is not done and has no new date → it appears under Earlier unfinished.
  If you plan it for Friday, it leaves the list.
- **b — Also include unfinished tasks that were never planned.**
- **c — Only past days of the current week.**

**Recommended: a.** It catches slipped work without clutter, and the Projects
screen already shows never-planned work.
**Cost to change later:** moderate; this needs separate data work, which is
already listed as open.

## U5 — Font in the Figma mock-ups

**Question.** Is it fine that the Figma mock-ups use Inter, because Figma could
not load Apple's system font, while the real app keeps using the Mac system font?

- **a — Yes: Inter in Figma only; the app keeps the system font** (as built).
- **b — Use Inter in the app too**, so it matches the mock-ups exactly.
- **c — Try again to load the Apple font in Figma.**

**Recommended: a.** The app already uses the system font; this only labels the
mock-ups honestly.
**Cost to change later:** small either way.

---

## Answers

Recorded only from your replies in the chat, with the date. Empty means open.

| # | Answer | Date | Recorded in |
| --- | --- | --- | --- |
The user's reply, 2026-11-11: "yes accept every recommended choices".

| # | Answer | Date | Recorded in |
| --- | --- | --- | --- |
| A1 | a — delete only while unused | 2026-11-11 | `AGENTS.md`; actions review |
| A2 | a — restore exact previous time | 2026-11-11 | `AGENTS.md`; actions review |
| A3 | a — no Undo for timers | 2026-11-11 | `AGENTS.md`; actions review |
| A4 | a — one change, at most 4 questions | 2026-11-11 | `AGENTS.md`; actions review |
| A5 | a — server re-checks everything | 2026-11-11 | `AGENTS.md`; actions review |
| U1 | b — 60 px | 2026-11-11 | `AGENTS.md`; R24 UX review |
| U2 | c — decide after a browser layout test (still to run) | 2026-11-11 | `AGENTS.md`; R24 UX review; `docs/PROGRESS.md` |
| U3 | a — Monday's month | 2026-11-11 | `AGENTS.md`; R24 UX review |
| U4 | a — as proposed | 2026-11-11 | `AGENTS.md`; R24 UX review |
| U5 | a — Inter in Figma only | 2026-11-11 | `AGENTS.md`; R24 UX review |

No answer needs an application code change, so nothing was added to the roadmap's
"Later" list.
