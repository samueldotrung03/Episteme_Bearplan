# Refinement tickets

Each ticket fits one session. Read the [entrypoint](README.md) first. Paths are
relative to the repository root. "User decides" marks a point where the agent
stops and asks; "User does" marks an action only the user performs.

---

## RF-01 — Rebaseline the roadmap

**Problem.** `BearPlans_Dated_Roadmap.md` carries a status line dated October 23
that says backup, AI and integrations have not started; all three are built. The
"Assistant actions" row is marked not started although it passed its evaluation.
Every date has passed, including the October 31 alpha decision. The build-status
table that used to be in `docs/PROGRESS.md` now exists only in Git history.

**Files.** `BearPlans_Dated_Roadmap.md` only.

**Steps.**

1. Recover the old build-status table: `git show 605826e:docs/PROGRESS.md`, read
   the "Build status" section. Cross-check each row with `docs/COMPLETED.md`
   (grep headings first; do not read all 3,000 lines) and the linked review.
2. Replace the status paragraph at the top with a dated one that matches evidence.
3. Keep the October daily table as history under a heading "Original October
   schedule (historical)". Correct only the status marks that evidence contradicts.
4. Add a new section **"Current plan"** above it with three parts:
   - **Now** — the active slice from `docs/PROGRESS.md` and its exit condition.
   - **Next** — ordered: close the task-entry slice → new core-trial candidate
     (RF-04) → seven-day trial → alpha decision.
   - **Later** — work that waits for the trial result: remaining UX screens,
     broader assistant acceptance, Canvas/Gmail, larger replans.
5. Add a **"Milestone status"** table: milestone, built (yes/partly/no),
   implementation evidence (link), open gate, gate owner (User/Agent).
6. Propose target dates for the Next items. **User decides** the dates; until
   they answer, write "date not set" rather than inventing one.

**Acceptance.**

- No statement in the file is contradicted by `docs/COMPLETED.md` or the tree.
- Every milestone row has an evidence link that resolves.
- The file states which day it was last updated and that dates are targets.
- Link check: every relative link in the file points to an existing path.

---

## RF-02 — Gate register and a limit on waiting work

**Problem.** Work is delivered "with follow-ups" or "pending the user's hands-on
check" faster than the user can check it. Open gates are spread across the
progress file and many reviews, so nobody can see the queue.

**Files.** New `docs/GATES.md`; a short rule added to `AGENTS.md`
("Verification, reviews and handoff" section); one link from `docs/PROGRESS.md`.

**Steps.**

1. Collect every open manual gate from `docs/PROGRESS.md` ("Open follow-ups and
   gates"), the historical snapshot `605826e:docs/PROGRESS.md` ("Pending manual
   gates", "Open follow-ups") and the reviews they link.
2. Write `docs/GATES.md` as one table: ID, what must be checked, in plain words;
   owner (User/Agent); what the owner needs to do and roughly how long; what it
   blocks; evidence link; date opened. Sort by what blocks the core trial first.
3. Mark each gate as one of: **blocks the trial**, **blocks the alpha**, or
   **can wait**. Propose which "can wait" gates to close as "accepted as
   unverified" — **User decides**; do not close any yourself.
4. Draft this rule and show the user the exact text before editing `AGENTS.md`:
   *"No new build starts while more than three user-owned gates in
   `docs/GATES.md` block the trial or the alpha. Close or explicitly defer one
   first. Every delivery that leaves a user check open adds a row there."*
   **User decides** the number and the wording.
5. Replace the gate bullets in `docs/PROGRESS.md` with a link to `docs/GATES.md`
   only if that section is not being edited by the active UX slice; otherwise add
   the link and leave the bullets.

**Acceptance.**

- Every gate named in the current and historical progress files appears once.
- Each row has an owner and a concrete action a non-engineer can follow.
- The `AGENTS.md` rule is present only if the user approved its text.

---

## RF-03 — Decision sheet for the user

**Problem.** Assistant defaults 2–6 and several UX defaults have waited on the
user since November 1. They are described in engineering language inside long
reviews, which makes them slow to answer.

**Files.** New `docs/plans/refinement/DECISIONS_FOR_USER.md`; after the user
answers, the affected rule in `AGENTS.md` and a dated note in the source review.

**Steps.**

1. Read the open decisions: `docs/reviews/2026-11-01-assistant-actions.md`
   (defaults 2–6) and the UX items listed in `docs/PROGRESS.md` (row height,
   breakpoint, cross-month week filing, "Earlier" selection, Figma font fallback).
2. For each, write: the question in one plain sentence; what happens in the app
   under each choice, with a small example; the recommended choice and why; what
   it costs to change later. No ticket IDs without an explanation.
3. Ask the user to answer in the chat. **User decides** every item.
4. Record each answer where the rule lives, dated, as a user decision. Remove the
   item from the open list in `docs/PROGRESS.md`. Do not change application code;
   if an answer requires a code change, add it to RF-01's "Later" list.

**Acceptance.**

- Each open decision has a question the user can answer with one word or letter.
- After the session, every item is either answered and recorded or still listed
  as open; none is silently treated as decided.

---

## RF-04 — New core-trial candidate and trial start

**Depends on:** the UX task-entry slice being closed in `docs/PROGRESS.md`.
Do not start while it is active.

**Problem.** The trial candidate was frozen on November 1 at schema 16. The
application is now at schema 24 with a different interface. The seven-day trial
has not started, so nothing built since October has been tested by real use.

**Files.** `docs/CORE_TRIAL_CHECKLIST.md`, a new candidate manifest and readiness
review under `docs/reviews/`, `docs/GATES.md`, `BearPlans_Dated_Roadmap.md`.

**Steps.**

1. **User decides** the trial scope: (a) the whole current app, including the
   assistant and connections, or (b) the local core only, with assistant and
   connections switched off or ignored. Recommend (a) for daily use with only the
   core counted for the alpha decision, and say why.
2. Confirm a clean tree for application code. Run the full check set on macOS
   and record exact results: `.venv/bin/python -m pytest`, `npm --prefix frontend
   test`, `npm --prefix frontend run typecheck`, `npm --prefix frontend run build`.
3. Verify upgrade on a **copy** of real data, never the live database: take a
   backup through the app's backup path, restore it to a disposable
   `BEARPLANS_DATA_DIR`, launch, and confirm migrations reach 24 and records load.
4. Write the readiness review and a new candidate manifest (commit, schema
   version, build fingerprint, test totals, known open gates).
5. Update `docs/CORE_TRIAL_CHECKLIST.md`: new candidate, how to launch, the
   Day 1 entry to fill in, and a five-line daily note format.
6. **User does:** tag the candidate commit and start Day 1. Give them the exact
   `git tag` command and the launch command.
7. Add the freeze rule to `docs/PROGRESS.md` for the trial week: only fixes for
   problems found in the trial, plus documents and tooling. New features wait.

**Acceptance.**

- All four check commands pass on the candidate, with totals recorded.
- The restore-and-upgrade check on a data copy passed and is recorded.
- The checklist names the new candidate and has an empty Day 1 entry ready.
- `docs/GATES.md` shows the trial as started only after the user reports Day 1.

---

## RF-05 — Repository cleanup

**Problem.** About 30 untracked `"… (1)"` files and folders (roughly 120 MB,
including `frontend (1)/`, `tests (1)/`, `tools (1)/`) sit beside the real files.
They are older copies dated October 27 to November 1 and differ from the tracked
versions. A search or an agent can pick up the stale copy. Separately, `main` is
54 commits ahead of the remote, so the only full copy of a month of work is this
laptop, and no release is tagged.

**Files.** New `docs/reviews/2026-11-XX-duplicate-inventory.md`. No tracked file
is changed.

**Steps.**

1. List every path matching `* (1)*` at any depth, excluding `node_modules`.
2. For each file, find out whether its content exists in Git history:
   `git hash-object "<file>"` then `git cat-file -e <hash>` (exit 0 means the
   exact content was committed at some point). For folders, do this per file,
   skipping `node_modules`, `dist` and `__pycache__`.
3. Write the inventory: path, size, modified date, and one of **exact copy of a
   committed version**, **differs from every committed version**, or **generated
   output**. For any file in the second group, summarize what is different.
4. Recommend: move everything to a dated folder outside the repository (for
   example `~/Desktop/BearPlans-duplicates-2026-11-11/`) rather than deleting.
   **User decides.** Only after an explicit yes, move the files and confirm
   `git status` shows no `(1)` paths and the test suites still pass.
5. **User does:** push `main`. Give the command and the count of commits that
   will be published. Remind them to check that no credential is tracked:
   `git ls-files | grep -iE 'secret|\.env|token\.json'` should list only source
   and test files.
6. Update the handoff note in `docs/PROGRESS.md` that says to preserve the `(1)`
   files once they are gone.

**Acceptance.**

- The inventory covers every `(1)` path and classifies each one.
- Nothing was moved or deleted without the user's yes in the chat.
- After the move: no `(1)` paths in `git status`; backend and frontend suites pass.

---

## RF-06 — One command for every check

**Problem.** The checks are strong but run only when an agent remembers. There
is no single command, no hook and no CI, and no linter.

**Files.** New `tools/check.py`; a "Checks" paragraph in `AGENTS.md` (Commands
section) and `README.md`; optionally `.github/workflows/checks.yml`.

**Steps.**

1. Write `tools/check.py` using only the standard library. It runs, in order,
   stopping at the first failure: frontend typecheck, frontend tests, frontend
   build, backend tests. Flags: `--fast` skips tests marked `e2e` (real-browser
   tests, which need Chrome and take several minutes); default runs everything.
   It sets `BEARPLANS_SECRETS_FILE` to an empty value and a disposable
   `BEARPLANS_DATA_DIR` so it cannot touch real data. It prints one summary line
   per step with the totals and exits non-zero on any failure.
2. Run it both ways and record times and totals in a short review.
3. Document it in `AGENTS.md` and `README.md` as the command to run before any
   handoff that changed code.
4. **User decides** two optional extras; do neither without a yes:
   - a `pre-push` Git hook that runs `tools/check.py --fast` (give the install
     command; hooks are local and not committed);
   - a GitHub Actions workflow running the fast set on push. Confirm first that
     the repository is private or that the user accepts logs being visible.
5. Linting is out of scope here. Note it as a follow-up: adding `ruff` and
   `eslint` is a dependency change and will produce a large first diff.

**Acceptance.**

- `python tools/check.py --fast` and `python tools/check.py` both pass on macOS,
  and a deliberately broken test makes the command exit non-zero.
- The script never reads the real data folder or secrets file.
- No new runtime or development dependency was added.

---

## RF-07 — Documentation map

**Problem.** The user asked for a frontend/backend/shared-tests ownership and
documentation map; `docs/PROGRESS.md` lists it as not started. There are more
than 100 review files and several plan folders, and no page that says which
document answers which question.

**Files.** New `docs/README.md`; one link each from `AGENTS.md` and `README.md`.

**Steps.**

1. Write a one-page map with three tables:
   - **Where to look** — question → document. For example: "What is active
     now?" → `docs/PROGRESS.md`; "What is waiting on me?" → `docs/GATES.md`;
     "What is the plan?" → roadmap; "What was finished and how was it checked?"
     → `docs/COMPLETED.md`; "What are the rules?" → `AGENTS.md`.
   - **Who owns what** — area (backend domain, routes, storage, frontend,
     browser tests, design files, plans) → folder → entry document → which
     checks apply.
   - **Document lifecycle** — which files are living (edited in place), which
     are append-only logs, and which are frozen history (reviews).
2. State the size limits that keep this working: `docs/PROGRESS.md` under about
   100 lines; reviews are never edited after their ticket closes, only linked.
3. Do not move or rename any existing document.

**Acceptance.**

- Every top-level document and plan folder appears in the map.
- A new agent can answer "what is active, what is next, what is waiting on the
  user" by following at most two links from `docs/README.md`.
- All links resolve.

---

## RF-08 — Closing re-evaluation

**Depends on:** RF-01 to RF-07 closed or explicitly deferred by the user.

**Files.** New `docs/reviews/2026-11-XX-refinement-closing.md`; `STATUS.md`.

**Steps.**

1. Re-run the checks from [BASELINE.md](BASELINE.md) and re-score the same 13
   aspects using the same evidence rules. Do not raise a score without pointing
   at what changed.
2. List what this plan did not fix and whether it still matters.
3. Mark the plan closed in `STATUS.md` and remove the pointer section from
   `docs/PROGRESS.md`.

**Acceptance.** The review shows before and after for each aspect, each with
its evidence, and names any ticket that was deferred and why.
