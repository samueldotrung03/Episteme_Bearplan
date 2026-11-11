# BearPlans refinement plan — agent entrypoint

Created November 11, 2026 from the project evaluation of the same date.
This folder is a self-contained work package for any agent (Claude or Codex).
It does not replace [AGENTS.md](../../../AGENTS.md); those rules apply to every ticket here.

## Goal

Make the project as easy to track as it is to build. The evaluation scored
execution at about 86/100 and trackability at about 60/100. The work here closes
that gap without adding product features.

Done means: the roadmap tells the truth, every open gate has an owner, the
seven-day core trial has a current candidate and a start date, the repository is
clean and pushed, and one command runs every check.

## Files in this folder

| File | Use |
| --- | --- |
| [STATUS.md](STATUS.md) | Ticket board and the session handoff log. **Read first, update last.** |
| [TICKETS.md](TICKETS.md) | Each ticket: scope, steps, files, acceptance checks, who decides what. |
| [BASELINE.md](BASELINE.md) | The November 11 scorecard and evidence, for the closing comparison. |
| [PROMPTS.md](PROMPTS.md) | Copy-paste prompts the user gives an agent to start, continue or hand off. |

## Session protocol

**Start of a session**

1. Read `AGENTS.md`, then `docs/PROGRESS.md`, then `STATUS.md` in this folder.
2. Run `git status --short | grep -v '(1)'` and `git log --oneline | head -5`.
   Compare with the last handoff entry in `STATUS.md`. If they disagree, say so
   before doing anything else; the tree is the truth, not the note.
3. Take the ticket the user named. If none was named, take the first ticket in
   `STATUS.md` that is `Ready`. Take one ticket only.
4. Tell the user in two or three sentences what you will do, then start.

**During a session**

- One ticket at a time. Finish it or stop it cleanly; do not start a second.
- Stay inside the ticket's listed files. If a ticket needs a file outside its
  list, stop and ask.
- A step marked **User decides** needs the user's answer in the current chat.
  A proposed default is not a decision.

**End of a session** (also when usage is running low — do this before anything else)

1. Update the board row in `STATUS.md`.
2. Add a handoff entry at the top of the log in `STATUS.md` using its template.
3. Update the "Refinement plan" pointer in `docs/PROGRESS.md` (active ticket and
   next step, at most five lines).
4. If a ticket finished, add a dated entry at the top of `docs/COMPLETED.md`.
5. Give the user: what changed, what was checked and the result, what is left,
   and a proposed commit message with the exact file list. **Do not commit, tag
   or push.** The user does those.

## Rules specific to this plan

- **No product features.** If a ticket seems to need application behavior to
  change, stop and report it. The only code this plan adds is the check script
  in RF-06.
- **Do not touch another agent's in-progress work.** The UX task-entry slice is
  active (see `docs/PROGRESS.md`). Leave `frontend/src/`, its tests and its
  review files alone, including uncommitted changes.
- **Do not delete, move or rewrite the `(1)` duplicate files** before the user
  approves RF-05's inventory. Never read a `(1)` file as a source of current
  truth; they are older copies.
- **Evidence over summaries.** A status you write must link the review, commit or
  command result that supports it. If you cannot find evidence, write
  "not verified" rather than a pass.
- **Write for the user.** They are the project owner, not a full-time engineer.
  Explain ticket IDs and terms the first time, state results before detail, and
  keep any list of actions for the user short and concrete.
- **Report honestly.** If a check fails or was skipped, say so with the output.

## Ticket order

`RF-01 → RF-02 → RF-03 → RF-05 → RF-06 → RF-07` can start now; they are documents
and tooling and do not collide with the active UX slice. `RF-04` (core trial)
waits until the task-entry slice is closed. `RF-08` is last.
