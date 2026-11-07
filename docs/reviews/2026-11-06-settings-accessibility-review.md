# APP-C08.2 — Settings browser review

**In progress.** On macOS 26.6.2 arm64, installed Chrome and disposable
data, six Settings combinations at 640 × 800, 800 × 900 and 1440 × 900 in
Light and Dark passed. Each exposed both provider entry points, had no
document-level horizontal overflow and opened the labeled bCourses dialog
with Enter. Escape closed the dialog and restored focus to its trigger.
No page errors were recorded.

The 640 Dark dialog and 1440 Light Settings screenshots were visually
inspected. They showed the expected controls and visible focus. Screenshots
were generated in the temporary directory /tmp/bearplans-c082-evidence.
The other four combinations were checked by browser assertions.

The broader Settings, Google and bCourses browser suite passed 14 tests.
The production frontend build passed in /tmp/bearplans-c082.6Q98VW.
The pytest run used Chrome, disposable storage, fake providers, and
`-p no:cacheprovider -p tests.connections_sandbox`. It set
`backend.platform.paths.FRONTEND_DIST` to the fresh temporary build.

Remaining before completion: actual browser 200% zoom and reflow, targeted
assistive-technology behavior, and visual inspection of the other captured
width/theme combinations. Existing keyboard tests cover dialog retry and
accessible field errors, but they do not establish a screen-reader result.

## Additional review

Visually inspected Settings in all six Light/Dark and 640/800/1440
combinations. The provider controls and text were visible in these captures.
A targeted Chrome accessibility-tree test passed for the bCourses token
failure. Chrome exposed the named dialog, named token input, associated error
description and alert role, and focus returned to the input after failure.

Command used the same disposable build and guard described above, with
`tests/test_settings_browser.py::test_credential_error_exposes_name_and_description_in_accessibility_tree`.
Result was one passed. This checks browser accessibility semantics, while
actual screen-reader output remains unverified. Actual 200% browser zoom
also remains unverified.
