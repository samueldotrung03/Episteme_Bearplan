# Task capture title accessibility — November 11, 2026

**Result: Pass with follow-ups.** The overlong-title message is now associated
with the title input through `aria-describedby`, and the input exposes
`aria-invalid` while the error is present. Correcting the title clears both.
The form test verifies the accessible description, invalid state and disabled
save, then verifies their recovery after correction.

On macOS Darwin arm64, the in-app browser and a disposable schema-24 service
showed the error for 201 characters, then removed it and enabled Add task after
correction. The test tab was closed and the service stopped. The browser check
did not test a screen reader. `npm --prefix frontend test` passed 212 tests in
19 files and `npm --prefix frontend run build` passed including typecheck.
Real browser storage/lock faults, broader accessibility and user acceptance
remain open.
