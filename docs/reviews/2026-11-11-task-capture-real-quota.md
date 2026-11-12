# Task capture browser storage failure — November 11, 2026

**Pass for G-01 (storage failure).** On macOS, an isolated headless Chrome
profile and a local service with disposable data were used. Browser storage was
filled with a synthetic value by binary search until Chrome itself raised
`QuotaExceededError` for any further key. Submitting a synthetic task then
showed the storage-unavailable alert, retained an editable title and sent no
request to `/api/task-captures`. The disposable service was stopped afterward.

Command: `PYTHONPATH=. .venv/bin/python /private/tmp/bearplans-storage-quota-check.py`
(passed; localStorage accepted 5,242,868 filler characters before the quota).
The script and test data are disposable. This is a real browser quota failure,
not a simulated API exception; it does not verify denied storage access or an
actual Web Locks failure. Those separate failure mechanisms have simulated tests
but are not claimed as real-browser passes. This evidence covers the storage
alternative in G-01, not user acceptance or the presentation matrix.
