# Task capture recovery focus — November 11, 2026

**Result: Pass with follow-ups.** An uncertain save replaces the submit control
with Check save status. The form now focuses that control when it becomes available;
after a definitive rejection it focuses the editable title. Existing replay and
revalidation rules are unchanged. Form tests cover both transitions.

On macOS Darwin arm64, used the in-app browser and a disposable schema-24
service. Stopping the service before submitting a synthetic task produced an
uncertain save and focused Check save status. Restarting the service and pressing
Enter saved the task and returned focus to Add task. The tab was closed and the
service stopped. The rejected-save focus transition was tested in the simulated
form test, not in the browser or with a screen reader.

`npm --prefix frontend test` passed 212 tests in 19 files and `npm --prefix
frontend run build` passed including typecheck. Real browser storage/lock faults,
broader theme and accessibility coverage, and user acceptance remain open.
