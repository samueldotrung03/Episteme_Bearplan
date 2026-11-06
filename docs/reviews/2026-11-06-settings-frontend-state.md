# APP-C03.2 Settings frontend status mapping

November 6, 2026 · implementation review · **Pass with follow-ups**

The typed client covers the write-only credential status from Connections
and the separate Google and bCourses provider responses. It preserves the
service error code, field, message and HTTP status. Settings can consume the
existing same-origin reads with an AbortSignal. The credential status reader
is available to the future Settings shell. The current provider views use their
existing runtime status endpoints.

The Google view distinguishes a missing or unusable file, a valid setup awaiting
sign-in, saved sign-in, an active browser attempt, permissions, account review,
active work, Pause and full sync history. Current mapping counts are shown only
for a verified account. The Disconnect message uses the mutation receipt for
revocation confirmation. Full sync evidence retains the timestamp and outcome of
prior runs, which may predate the current saved grant. The browser attempt ID
and account review key are typed for later controls and stay out of the view.

A superseded Google status read is aborted and its response is ignored even if
it finishes after abort. Polls avoid overlapping a newer local action or read.
Leaving the view cancels status and picker reads. Reopening waits for a current
status before the automatic picker path runs. Already-started writes may finish.
A failed action keeps its own error if the status readback also fails. The
previous provider snapshot stays visible with a status retry action.

bCourses can retry its first local read. Refresh history appears beside the
cached assignments, even if the last refresh was rejected. When saving followed
courses fails, readback can update saved course state while retaining the user's
selection for retry. These changes use the existing routes, provider triggers,
credential storage and task records.

## Verification

macOS 26.6.2 on arm64, Node 24.21.0 and Python 3.13.15. The Chrome check used
the temporary production bundle, disposable data and simulated Google
providers under the outbound urllib guard. It exercised following a calendar,
adding an event in Plan, syncing, background task completion, and narrow
Google layout at 1440 × 1000 and 375 × 850.

```sh
npm --prefix frontend test -- src/Google.test.tsx src/BCourses.test.tsx src/api.test.ts
npm --prefix frontend test
npm --prefix frontend run typecheck
bp_build_dir=$(mktemp -d /tmp/bearplans-settings-client-build.XXXXXX)
npm --prefix frontend run build -- --outDir "$bp_build_dir"
BP_BROWSER_DIST="$bp_build_dir" BEARPLANS_E2E_CHANNEL=chrome .venv/bin/python - <<'PY'
import os
from pathlib import Path

import pytest
from backend.platform import paths

paths.FRONTEND_DIST = Path(os.environ["BP_BROWSER_DIST"])
raise SystemExit(pytest.main(["-q", "-p", "no:cacheprovider", "-p", "tests.connections_sandbox",
                              "tests/test_google_browser.py"]))
PY
git diff --check
```

- The focused run passed 25 tests before the final navigation guard. The final
  full Vitest run passed 175 tests in 15 files. Type checking, the temporary
  build, the Chrome Google flow and the scoped diff check passed.
- The **UI-01 state/readback subset** covers setup and authorization differences,
  missing permissions, account review, paused stale evidence, action and readback
  failure together, out-of-order replies after navigation, revocation uncertainty,
  saved bCourses history and course-draft retention.
- The Settings shell and panel review remain APP-C05. Credential form input
  handling, explicit Google authorization cancellation and account recovery
  controls belong to the later provider UI slices. APP-C04 covers scheduler
  acknowledgement and trigger gating. Live provider and hands-on Settings
  acceptance remain open.

[Backend contract](2026-11-06-settings-backend-status.md) ·
[Execution plan](../../frontend/plans/settings-connections/EXECUTION_PLAN.md) ·
[Shared progress](../PROGRESS.md)
