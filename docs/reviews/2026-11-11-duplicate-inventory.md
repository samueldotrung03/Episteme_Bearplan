# Duplicate `" (1)"` file inventory — 2026-11-11 (refinement RF-05)

**Result: nothing in the 47 `" (1)"` paths is unique.** All but two source and
document copies match a version committed under the real (non-`(1)`) path. The
other two (`README (1).md`, `docs/PROGRESS (1).md`) are drafts of the `7e38d7c`
versions, with no lines of their own (see the correction below). The evidence
folders and sleep-probe logs were never in Git, but each one matches an
original byte for byte. Everything else is generated output. Moving all 47
paths out of the repository loses no work.

**Correction (same day, after the move).** The ticket assumed these files were
untracked. In fact, 4,453 `(1)` files, including `frontend (1)/node_modules`,
were committed in `5687685` ("Update refinement plan"), which is already on
`origin`. So the first history check (`git cat-file -e`) passed trivially:
the duplicates' own commit holds their content. The check was rerun against a
blob list from every commit with all `(1)` paths excluded:
112 of 114 files match a version committed under the real path. The two
others were diffed against their closest version, `7e38d7c`. `README (1).md`
is that version minus the "Project folder" section. `docs/PROGRESS (1).md` is
that version minus the November 1 status section, plus two older milestone
table rows that are already present in three commits. Neither has content found
nowhere in history.

## Method

- Paths: `find . -name '* (1)*'` at any depth, excluding `.git` and
  `node_modules`, keeping only the outermost `(1)` path (a `(1)` folder counts
  once). Result: 47 paths (6 folders, 41 files), about 152 MB on disk
  (`du -sck`), 115 MB of it in `frontend (1)/node_modules`.
- History check per file: `git hash-object <file>` then `git cat-file -e <hash>`;
  exit 0 means that exact content was committed at some point. Folders were
  checked file by file, skipping `node_modules`, `dist`, `__pycache__` and
  `.pytest_cache`.
- Original check: `cmp` against the same path without ` (1)`; for the two
  `.evidence` folders, `diff -rq` against the original folder.
- `.evidence/` and `sleep-probe-*.jsonl` are excluded by `.gitignore` (lines 20–21),
  which is why they are not in history.
- The script and its raw output were kept in the session scratchpad, not in the repository.

## Classes

- **Exact copy of a committed version.** The same content is in Git history,
  usually an older version that the current file has since replaced.
- **Exact copy of an ignored original.** Never committed because `.gitignore`
  excludes it, but identical to the file or folder beside it.
- **Generated output.** Python bytecode, pytest cache, frontend build and
  installed packages, all recreated by the normal commands.
- **Differs from every committed version and from the original.** **None found.**

## Folders

| Path | Size | Modified | Class | Detail |
| --- | --- | --- | --- | --- |
| `frontend (1)/` | 116M | 2026-11-02 | Exact copy of committed + generated | 33 files in history; 4 `dist/` build files; plus `node_modules/` (115M) |
| `tests (1)/` | 3.8M | 2026-11-02 | Exact copy of committed + generated | 53 files in history; 74 `__pycache__` files |
| `tools (1)/` | 140K | 2026-11-02 | Exact copy of committed + generated | 2 files in history; 5 `__pycache__` files |
| `.evidence/daily-streaks (1)/` | 29M | 2026-11-02 | Exact copy of ignored original | 137 files; `diff -rq` against `.evidence/daily-streaks/`: no differences |
| `.evidence/mac-verification-20261101 (1)/` | 1.9M | 2026-11-02 | Exact copy of ignored original | 52 files; `diff -rq` against `.evidence/mac-verification-20261101/`: no differences |
| `__pycache__ (1)/` | 12K | 2026-11-02 | Generated output | 1 bytecode file |

## Files

"Same as current" means the file without ` (1)` has identical content today;
"older" means the current file has changed since, and the copy matches an
earlier commit.

| Path | Size | Modified | Class | vs current |
| --- | --- | --- | --- | --- |
| `.gitattributes (1)` | 4.0K | 2026-10-27 | Committed copy | same as current |
| `.gitignore (1)` | 4.0K | 2026-10-13 | Committed copy | older |
| `AGENTS (1).md` | 20K | 2026-10-27 | Committed copy | older |
| `BearPlans_Build_Plan (1).md` | 24K | 2026-10-27 | Committed copy | older |
| `BearPlans_Build_Review_Plan (1).md` | 16K | 2026-10-27 | Committed copy | same as current |
| `BearPlans_Dated_Roadmap (1).md` | 12K | 2026-10-27 | Committed copy | older |
| `CLAUDE (1).md` | 4.0K | 2026-10-15 | Committed copy | older |
| `README (1).md` | 28K | 2026-11-01 | Committed copy | older |
| `launch (1).py` | 8.0K | 2026-10-22 | Committed copy | same as current |
| `pyproject (1).toml` | 4.0K | 2026-11-01 | Committed copy | same as current |
| `requirements (1).lock` | 4.0K | 2026-11-01 | Committed copy | same as current |
| `requirements-dev (1).lock` | 4.0K | 2026-11-01 | Committed copy | same as current |
| `backend/app (1).py` | 12K | 2026-11-01 | Committed copy | older |
| `backend/domain/assistant (1).py` | 8.0K | 2026-11-01 | Committed copy | older |
| `backend/domain/assistant_tools (1).py` | 8.0K | 2026-11-01 | Committed copy | older |
| `backend/domain/planning (1).py` | 12K | 2026-10-21 | Committed copy | older |
| `backend/domain/projects (1).py` | 4.0K | 2026-10-13 | Committed copy | older |
| `backend/domain/statistics (1).py` | 8.0K | 2026-10-27 | Committed copy | older |
| `backend/domain/tasks (1).py` | 16K | 2026-10-16 | Committed copy | older |
| `backend/domain/weeks (1).py` | 16K | 2026-10-15 | Committed copy | older |
| `backend/platform/ollama (1).py` | 8.0K | 2026-11-01 | Committed copy | older |
| `backend/routes/assistant (1).py` | 4.0K | 2026-11-01 | Committed copy | older |
| `docs/PROGRESS (1).md` | 120K | 2026-11-01 | Committed copy | older |
| `docs/reviews/2026-10-20-coins-shop (1).md` | 16K | 2026-10-20 | Committed copy | older |
| `docs/reviews/2026-10-20-m3-growing-forest (1).md` | 12K | 2026-10-20 | Committed copy | older |
| `docs/reviews/2026-10-21-daily-streaks (1).md` | 16K | 2026-10-21 | Committed copy | older |
| `sleep-probe-20261013-213338 (1).jsonl` | 4.0K | 2026-10-13 | Copy of ignored original | same as current |
| `sleep-probe-20261013-213557 (1).jsonl` | 56K | 2026-10-13 | Copy of ignored original | same as current |
| `sleep-probe-20261013-213942 (1).jsonl` | 72K | 2026-10-13 | Copy of ignored original | same as current |
| `sleep-probe-20261013-214846 (1).jsonl` | 104K | 2026-10-13 | Copy of ignored original | same as current |
| `.pytest_cache/v/cache/nodeids (1)` | 92K | 2026-11-01 | Generated output | — |
| `backend/__pycache__/app (1).cpython-313.pyc` | 16K | 2026-11-01 | Generated output | — |
| `backend/domain/__pycache__/assistant (1).cpython-313.pyc` | 12K | 2026-11-01 | Generated output | — |
| `backend/domain/__pycache__/assistant_tools (1).cpython-313.pyc` | 12K | 2026-11-01 | Generated output | — |
| `backend/domain/__pycache__/planning (1).cpython-313.pyc` | 16K | 2026-10-21 | Generated output | — |
| `backend/domain/__pycache__/projects (1).cpython-313.pyc` | 8.0K | 2026-10-13 | Generated output | — |
| `backend/domain/__pycache__/statistics (1).cpython-313.pyc` | 12K | 2026-10-27 | Generated output | — |
| `backend/domain/__pycache__/tasks (1).cpython-313.pyc` | 16K | 2026-10-16 | Generated output | — |
| `backend/domain/__pycache__/weeks (1).cpython-313.pyc` | 16K | 2026-10-15 | Generated output | — |
| `backend/platform/__pycache__/ollama (1).cpython-313.pyc` | 8.0K | 2026-11-01 | Generated output | — |
| `backend/routes/__pycache__/assistant (1).cpython-313.pyc` | 4.0K | 2026-11-01 | Generated output | — |

## Recommendation (user decides)

Move all 47 paths, keeping their relative locations, to a dated folder outside
the repository: `~/Desktop/BearPlans-duplicates-2026-11-11/`. Do not delete
them; once the move has been confirmed you can delete that folder whenever you
like. After the move, check that `git status` shows no `(1)` paths and that the
backend and frontend test suites pass.

The ticket estimated about 30 paths and 120 MB. The actual count is 47 paths
and about 152 MB, because nested bytecode files and the two evidence folders
are counted separately here.

## Decision and move

User answered "yes" in the chat on 2026-11-11. All 47 paths were moved with `mv -n`,
keeping their relative layout, to `~/Desktop/BearPlans-duplicates-2026-11-11/`
(152 MB). Afterwards `find` reports no `(1)` paths in the repository. Because the
files were tracked, `git status` now lists 4,453 `(1)` files as deleted (` D`).
They leave the repository only once the user commits that deletion. To undo
instead, move the folder contents back, or run `git restore` on the `(1)` paths.

Checks after the move: frontend `npm test` 213 passed (19 files);
`npm run build` succeeded. Backend result is recorded in `STATUS.md`.
