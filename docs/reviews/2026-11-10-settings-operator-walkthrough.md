# APP-C09.1 — Settings operator walkthrough

**Pass with follow-ups for the bounded walkthrough.** On macOS arm64, a disposable local service used a fake
bCourses rejection and blocked non-loopback urllib provider requests. The
user reported: “I closed VS code, and all the steps are clear and the taska
nad paused timer remain visible. Everything worked perfect.” The requested
steps covered the bCourses error, assignment review, a sample project/task,
and starting and pausing its timer. This is user-reported, not an observed
walkthrough or real-provider evidence.

The user confirmed the same task and paused timer remained available after
closing and reopening the browser tab. The disposable service was then stopped
gracefully and restarted with the same isolated database and fake-provider guard;
a loopback GET returned HTTP 200. The user confirmed the same task and paused
timer were still present after restart.

On November 11 the isolated service was restarted with a fake checker that
accepts two designated synthetic values and rejects others; provider requests
remain blocked. A loopback GET returned HTTP 200. The user confirmed that simulated credential setup, rejected replacement and
successful replacement were clear. A subsequent restart uses fake Google clients and synthetic sign-in files in
the disposable secrets directory, with non-loopback urllib transport blocked.
The user confirmed that Pause, Sync once while paused, and Resume worked and
that the controls and messages were clear. The user paused again; a loopback API check confirmed the paused state. The
disposable service was stopped gracefully and restarted with the same isolated
database and fake clients. The API still reported paused after restart; the
user confirmed Settings still showed Pause and offered Resume after refresh.

## Handoff and remaining evidence

This walkthrough used macOS arm64, the current built interface, disposable
`/tmp/bearplans-voiceover-20261106` data, synthetic credentials and fake
provider clients. It is user-reported and was not directly observed.
It supports local error recovery, task/timer continuity and Google Pause
persistence in this fixture. It does not establish a real provider connection,
an operator-tested same-account reconnect, full offline system behavior, or
the separate core-trial, hardware and release gates. Earlier automated results
and their exact environment are recorded in the linked integrated and create
guard reviews, not newly rerun here.

## Same-account and offline evidence check — November 11

On macOS arm64 at source commit `725168f`, ran `.venv/bin/python -m pytest
-q -p no:cacheprovider -p tests.connections_sandbox tests/test_google_account.py
tests/test_service_restart.py::test_google_pause_and_local_plan_survive_abrupt_service_restart`:
15 passed in 3.11 seconds. The account tests use fake providers and include
same-account mapping reuse and account isolation. The process test covers saved
Pause and local plan persistence across an abrupt service restart without a
Google grant. Earlier offline Plan regressions are described in the
[integrated review](2026-11-06-settings-integrated-regression.md). The user
also performed local planning and timer work in the fake-provider demo with
non-loopback urllib transport blocked. These checks do not establish real
Google reauthorization or a system-wide network-disconnected operator test.
