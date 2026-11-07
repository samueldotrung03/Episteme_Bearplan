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

## Narrow reflow follow-up

The existing `test_settings_returns_to_work_and_preserves_countdown`
passed again in installed Chrome with disposable data. It checks the Settings
page at a 320 CSS-pixel viewport in Dark mode, including horizontal overflow
and access to provider entry points. This is a narrow-reflow diagnostic.
Actual browser zoom was not measured.

A temporary browser profile and local test extension were used to attempt
Chrome's own tab zoom API. Installed Chrome loaded no extension worker, and
the previously available Chrome for Testing executable was unavailable. No
zoom result was claimed. VoiceOver output has not been observed. Both
checks remain open for an interactive browser and assistive-technology review.

## Actual Chrome 200% zoom

Chrome's Appearance settings in a disposable profile were set to 200%.
At a 640 × 800 browser viewport, Chrome reported a device pixel ratio of 2
and a 320 CSS-pixel viewport. The Settings entry points were reachable with
no page-level horizontal overflow.

The first capture exposed a dialog positioned partly below the viewport
after the page scrolled. Fixed the shared connection dialog to remain
centered in the viewport. The regression checks its bounds at 200%, scrolls
to the Cancel button, verifies it is in the viewport, and checks Escape
returns focus. A previous test attempt used a nonexistent Playwright
`is_in_viewport` method. Replacing it with the supported assertion produced
a clean rerun.

With the fresh /tmp/bearplans-c082zoom.MuQjzO build, the guarded Settings,
Google and bCourses browser suites passed 16 tests on macOS using installed
Chrome. Frontend tests passed 178 cases, typecheck and production build
passed. Actual VoiceOver output remains open.

## Google recovery accessibility-tree follow-up

The existing fake-provider Chrome recovery walkthrough passed with additional
assertions. The account-review dialog exposes its name and confirmation
button in Chrome's accessibility tree. Cancel receives initial focus, and
Escape returns focus to the review button. After an unconfirmed revocation,
the receipt exposes a status role. The guarded run of
`tests/test_google_browser.py::test_reviewed_account_recovery_and_offline_disconnect`
passed once on macOS using the /tmp/bearplans-c082zoom.MuQjzO build.
Spoken VoiceOver behavior is still awaiting the operator walkthrough.

The Google account-review walkthrough also passed a forward and reverse
keyboard check. Tab moved from Cancel to Use this account, and Shift+Tab
returned to Cancel before Escape restored focus to the trigger. This focused
test passed once with fake providers and the same disposable Chrome build.

## Preliminary implementation inspection

While the VoiceOver walkthrough is pending, inspected the Settings navigation,
credential dialogs, course selection, Google recovery controls and the
connection-related backend changes introduced since the Settings route.
The recorded provider and persistence results remain those in the individual
implementation reviews. The full tracked Settings change range passed
`git diff 88203e4^..HEAD --check`. This is a preliminary inspection by the
implementing agent. The planned independent final review remains open.
