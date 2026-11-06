# APP-C03.1 Settings backend status contract

November 6, 2026 · implementation review · **Pass with follow-ups**

Settings can read local setup, saved authorization, last check, provider history,
automatic-sync preference and active work separately. The reads contact neither
provider. The existing status routes carry the contract.

| Evidence | Field and interpretation |
| --- | --- |
| bCourses setup | `GET /api/connections` → `bcourses.set`, `checked_at`, `check_ok`, `check_message`. A saved token and its historical check can coexist with a later rejected refresh. |
| bCourses refresh | `GET /api/bcourses` → `sync.last_attempt_at`, `last_success_at`, `last_error`. A failed refresh retains the prior successful timestamp and cached data. |
| Google setup | `GET /api/connections` → `google.setup` and `GET /api/google` → `setup`. Values are `missing`, `unusable` and `configured`. Local setup uses the Desktop file format validator. The setup check receipt in Connections describes a local format check. |
| Google authorization | `GET /api/google` → `connected` means a matching saved grant exists. The active browser attempt, sign-in error and stored missing permissions are independent. None of these checks tests live access. |
| Google account | `tasks.account_status` is `unverified`, `verified`, `different_account` or `unowned_links`. A fresh grant is unverified until the account is checked. A review key is present only for the current verified candidate. A legacy `other_account` flag remains an alias for either review case. |
| Google activity | `activity` is `idle`, `syncing` or `refreshing_calendars`. `tasks.syncing` means full sync. `connection_changing` can coexist with active work while the connection change waits for it to drain. |
| Google preference and history | `tasks.paused_at` is the persisted automatic-sync preference. The `tasks` attempt, success and error fields describe the most recent **full** sync history. A Calendar-only refresh can verify the account without claiming full sync success. Pause and failures can coexist. History can predate the current grant. |
| Disconnect or setup removal | The mutation response reports `revoked: true` on acknowledged revocation and `false` when revocation was unconfirmed. `null` means no saved grant to revoke in that operation, or an ordinary status read with no operation receipt. |

The compact Google summary requires a verified account and recorded full sync
success before it can say `working`. Use the separate fields for
Settings copy. Persisted sync errors retain their existing safe messages. Status
does not infer a new provider error code from a historical message, an account
email from a grant or a timestamp for each Google function. This slice uses
the existing credential files and database schema.

## Verification

macOS 26.6.2 on arm64, Python 3.13.15 and Node 24.21.0. Guarded tests and
the targeted Chrome flow used fake providers and disposable paths. The urllib
guard allowed only loopback. No real credentials or saved user data were used.

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox \
  tests/test_connections.py tests/test_secrets_location.py tests/test_bcourses.py \
  tests/test_google_tasks.py tests/test_google_calendar.py tests/test_google_reading.py \
  tests/test_google_controls.py tests/test_google_account.py tests/test_api.py tests/test_assistant.py
bp_test_data=$(mktemp -d /tmp/bearplans-settings-status.XXXXXX)
BEARPLANS_DATA_DIR="$bp_test_data/data" .venv/bin/python -m pytest -q -p no:cacheprovider -m 'not e2e'
npm --prefix frontend test
npm --prefix frontend run typecheck
bp_build_dir=$(mktemp -d /tmp/bearplans-settings-status-build.XXXXXX)
npm --prefix frontend run build -- --outDir "$bp_build_dir"
git diff --check
```

- **DOC-03 and API-01:** checked the two-provider field mapping, missing and
  unusable setup, configured and signed out, missing permissions, never-synced,
  account verification without full sync, account review, expired saved grant,
  historical refresh evidence, and operation-scoped revocation.
- **API-09:** 229 guarded backend checks passed, including loopback and same-origin
  boundaries, structured errors, credential response and log canaries, and
  Assistant tool boundaries.
- **API-10 subset:** Pause preserved its original timestamp on replay and
  remained set across restart and one-shot failure. An injected SQLite write
  failure returned a structured error and left Pause unset until retry succeeded.
  Concurrent Disconnect distinguished full sync from calendar refresh while
  draining active work. Pause/Resume scheduler serialization remains APP-C04.
- **Backend regression:** 1,002 passed, one Windows-only test skipped and 21
  browser tests deselected. The targeted Chrome test below ran separately.
- **Frontend:** 167 Vitest checks passed. Type checking and the temporary
  production build passed. The targeted Chrome Calendar-to-Plan flow passed
  using the new bundle and the disposable provider fixture.
- **Handoff:** [progress](../PROGRESS.md),
  [test plan](../../frontend/plans/settings-connections/TEST_PLAN.md) and
  [execution plan](../../frontend/plans/settings-connections/EXECUTION_PLAN.md).
  TypeScript state mapping and readback belong to APP-C03.2. Live providers and
  hands-on Settings acceptance remain open.

Chrome command used the existing test with the temporary bundle override.

```sh
BP_BROWSER_DIST="$bp_build_dir" BEARPLANS_E2E_CHANNEL=chrome .venv/bin/python - <<'PY'
import os
from pathlib import Path

import pytest
from backend.platform import paths

paths.FRONTEND_DIST = Path(os.environ["BP_BROWSER_DIST"])
raise SystemExit(pytest.main(["-q", "-p", "no:cacheprovider", "-p", "tests.connections_sandbox",
                              "tests/test_google_browser.py"]))
PY
```
