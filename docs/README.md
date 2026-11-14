# BearPlans — documentation map

Created November 11, 2026 (refinement ticket RF-07). This page says which document
answers which question. It holds no status of its own: current state lives only in
[PROGRESS.md](PROGRESS.md), and open gates only in [GATES.md](GATES.md).
Paths below are from the repository root.

## Where to look

| Question | Document |
| --- | --- |
| What is active now, and what is next? | [docs/PROGRESS.md](PROGRESS.md) |
| What is waiting on me (the user)? | [docs/GATES.md](GATES.md) |
| What was finished, and how was it checked? | [docs/COMPLETED.md](COMPLETED.md) (newest first; links the review for each item) |
| What are the rules for every agent? | [AGENTS.md](../AGENTS.md); additions in [frontend/AGENTS.md](../frontend/AGENTS.md), [backend/AGENTS.md](../backend/AGENTS.md) and [tests/AGENTS.md](../tests/AGENTS.md) |
| Who edits what when two agents work at once? | "Parallel work" in [AGENTS.md](../AGENTS.md) |
| How does Claude resume or hand off? | [CLAUDE.md](../CLAUDE.md) |
| What is the plan and when is each part due? | [BearPlans_Dated_Roadmap.md](../BearPlans_Dated_Roadmap.md) (dates are targets) |
| What is the full product and build design? | [BearPlans_Build_Plan.md](../BearPlans_Build_Plan.md) |
| What must each build pass to be reviewed? | [BearPlans_Build_Review_Plan.md](../BearPlans_Build_Review_Plan.md) |
| How do I install, launch and use the app? | [README.md](../README.md) |
| How do I run every check? | `python3 tools/check.py` — see "Checks" in [AGENTS.md](../AGENTS.md) |
| What is the tracking/refinement work package? | [docs/plans/refinement/README.md](plans/refinement/README.md); board in its [STATUS.md](plans/refinement/STATUS.md); start/continue prompts in [PROMPTS.md](plans/refinement/PROMPTS.md) |
| Which product decisions has the user made? | [DECISIONS_FOR_USER.md](plans/refinement/DECISIONS_FOR_USER.md) and the gate/decision lists in PROGRESS |
| How does the local assistant work? | [docs/LOCAL_ASSISTANT.md](LOCAL_ASSISTANT.md) |
| How do I run the seven-day real-use trial? | [docs/CORE_TRIAL_CHECKLIST.md](CORE_TRIAL_CHECKLIST.md); notes template [CORE_TRIAL_NOTES_TEMPLATE.txt](CORE_TRIAL_NOTES_TEMPLATE.txt) |
| How do I back up and restore offline? | [docs/BACKUP_RESTORE_OPERATOR_CHECKLIST.md](BACKUP_RESTORE_OPERATOR_CHECKLIST.md) |
| How do I verify the core on the Mac (sleep, restart)? | [docs/MAC_CORE_VERIFICATION.md](MAC_CORE_VERIFICATION.md) |
| What is the UX design and its handoff? | [frontend/plans/README.md](../frontend/plans/README.md) (index of all frontend plans) |
| What evidence backs a past result? | `docs/reviews/YYYY-MM-DD-<feature>.md`, screenshots in `docs/reviews/evidence/` — follow the link from COMPLETED rather than browsing by filename |

## Who owns what

"Entry document" is what to read before changing the area. "Checks" are the parts
of `tools/check.py` that cover it; the full run is required before any code handoff.

| Area | Folder | Entry document | Checks |
| --- | --- | --- | --- |
| Domain rules (planning, timer, rewards, assistant) | `backend/domain/` | [AGENTS.md](../AGENTS.md) (product scope, weekly planning, architecture) | backend tests (`pytest`) |
| HTTP routes | `backend/routes/`, `backend/app.py` | [AGENTS.md](../AGENTS.md) (architecture and data safety) | backend tests |
| Storage and migrations | `backend/storage/` | [AGENTS.md](../AGENTS.md) (architecture and data safety) | backend tests, plus the upgrade/restart checks AGENTS.md requires for schema changes |
| Platform: paths, secrets, bCourses, Google, Ollama | `backend/platform/` | [AGENTS.md](../AGENTS.md); [LOCAL_ASSISTANT.md](LOCAL_ASSISTANT.md) for Ollama | backend tests |
| Frontend interface | `frontend/src/` (tests beside each file) | [frontend/AGENTS.md](../frontend/AGENTS.md) | frontend typecheck, tests, build |
| Browser journey tests | `tests/test_*_browser.py` (marked `e2e`) | [AGENTS.md](../AGENTS.md) (verification) | full `tools/check.py` run only; `--fast` skips them |
| Backend and integration tests | `tests/` | [AGENTS.md](../AGENTS.md) (verification) | backend tests |
| Design files (Figma records) | `frontend/design/` | [frontend/FIGMA_PROTOTYPE.md](../frontend/FIGMA_PROTOTYPE.md) | none in `tools/check.py`; reviewed by hand |
| Frontend plans | `frontend/plans/`, `frontend/BEARPLANS_UX_*.md` | [frontend/plans/README.md](../frontend/plans/README.md) | documentation checks (content, links, diff) |
| Project plans and roadmap | repository root `BearPlans_*.md`, `docs/plans/` | [BearPlans_Dated_Roadmap.md](../BearPlans_Dated_Roadmap.md) | documentation checks |
| Agent skills | `.agents/skills/`, `.claude/skills/` | each skill's `SKILL.md` | none |
| Developer tools and probes | `tools/` | [AGENTS.md](../AGENTS.md) (commands) | `tools/check.py` itself |

## Document lifecycle

| Kind | Files | How it changes |
| --- | --- | --- |
| **Living** — edited in place to stay true | `docs/PROGRESS.md`, `docs/GATES.md`, `AGENTS.md`, `frontend/AGENTS.md`, `CLAUDE.md`, `README.md`, this map, `BearPlans_Dated_Roadmap.md`, `docs/LOCAL_ASSISTANT.md`, `docs/plans/refinement/STATUS.md` (board), `frontend/plans/` indexes | Update whenever the fact changes; old state goes to COMPLETED or a review, not a second tracker. |
| **Append-only logs** — new entries at the top, old entries kept | `docs/COMPLETED.md`, the handoff log in `docs/plans/refinement/STATUS.md` | Add an entry; correct an old one only to fix a factual error, and say so. |
| **Stable references** — change rarely, by decision | `BearPlans_Build_Plan.md`, `BearPlans_Build_Review_Plan.md`, `docs/plans/refinement/TICKETS.md` and `PROMPTS.md`, operator checklists in `docs/`, `frontend/BEARPLANS_UX_*.md`, `frontend/FIGMA_PROTOTYPE.md` | Change when the plan or procedure itself changes; record why in PROGRESS or COMPLETED. |
| **Frozen history** | `docs/reviews/` and `docs/reviews/evidence/`, `docs/plans/refinement/BASELINE.md` | Never edited after its ticket closes, only linked. A newer review supersedes an older one. |

## Size limits that keep this working

- `docs/PROGRESS.md` should stay under about 100 lines: current work only. Move
  finished items to COMPLETED. (On November 11, 2026 it is 185 lines — over the limit.)
- Reviews are never edited after their ticket closes; link them instead.
- A handoff entry in the refinement log stays under 20 lines.
- Add a new document to this map when you create it; do not move or rename documents
  without updating every link.
