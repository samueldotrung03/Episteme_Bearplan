# Settings and connections — implementation handoff

Reviewed November 11, 2026, against source commit `e349552` on macOS arm64.
[Shared progress](../../../docs/PROGRESS.md) is the current status and gate
record. The [design handoff](HANDOFF.md) is a historical Figma snapshot.

## Delivered behavior

Settings is available from the app navigation and returns to the prior work
context. bCourses supports masked token setup and replacement, checking,
reviewed removal, course selection and assignment review; an assignment
becomes a task only on Add. Google setup reviews sharing before authorization;
account isolation, disconnect recovery and calendar/task synchronization are
implemented. Pause persists; Sync once keeps automatic sync paused; Resume
restores automatic synchronization. See [setup and use](../../../README.md#settings-and-connections).

Credentials are stored outside the database in the app data folder's `secrets/`
directory. User-confirmed Pause/Resume and planned-week decisions are distinct
from proposed reward defaults. Migrations 20–23 cover Google Pause, account
identity, account-scoped events and durable uncertain-create intents. The create
guard stops unconfirmed remote creates from being retried without review; an
explicit continuation may still produce a duplicate and cannot identify older
copies. It does not delete remote items.

## Evidence and limits

- The [design review](../../../docs/reviews/2026-11-04-settings-context-handoff.md)
  records the bounded Figma user walkthrough, not runtime acceptance.
- The [create-guard review](../../../docs/reviews/2026-11-06-google-create-guard.md)
  records 1,083 backend passes with one Windows-only skip, 180 frontend passes,
  build/typecheck and two fake-provider Chrome recovery checks on the reviewed
  build; these are historical results, not reruns for this document.
- The [accessibility review](../../../docs/reviews/2026-11-06-settings-accessibility-review.md)
  records width, theme, keyboard and 200% zoom checks and the user's bounded
  VoiceOver report.
- The [operator review](../../../docs/reviews/2026-11-10-settings-operator-walkthrough.md)
  records the user's disposable-data walkthrough, fake bCourses setup and
  replacement, fake Google Pause and service restart, and 15 focused account and
  restart checks. Provider calls were blocked; feedback was user-reported.

Real bCourses/Google authorization, real same-account reauthorization and a
whole-Mac offline operator test are not verified. Live provider checks are
optional and require separately established scope, including any remote writes;
see [test plan](TEST_PLAN.md#optional-operatorprovider-checks). Core trial,
Mac timer/hardware and release acceptance remain separate. No prototype or
simulated-provider result certifies these gates.
