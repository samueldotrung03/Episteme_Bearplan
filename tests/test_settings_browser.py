"""Verify Settings navigation with synthetic work and a disposable local service."""

import threading
import time

import pytest
import uvicorn

from backend.app import create_app
from backend.storage.db import open_database

from backend.platform.paths import FRONTEND_DIST
from tests.conftest import free_port, http_json
from tests.test_e2e_browser import browser, evidence, no_horizontal_overflow, playwright_sync

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not (FRONTEND_DIST / "index.html").is_file(), reason="frontend not built"),
]


@pytest.fixture
def settings_url(tmp_path):
    port = free_port()
    app = create_app(open_database(tmp_path / "settings.sqlite3"), FRONTEND_DIST)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.05)
        assert server.started
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(10)


def test_settings_returns_to_work_and_preserves_countdown(browser, evidence, settings_url):
    expect = playwright_sync.expect
    context = browser.new_context(viewport={"width": 640, "height": 800})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        _, project = http_json("POST", settings_url + "/api/projects", {"name": "Seminar"})
        _, task = http_json("POST", settings_url + "/api/tasks", {
            "title": "Read the primary source", "project_id": project["id"],
        })
        page.goto(settings_url)
        nav = page.get_by_role("navigation", name="Main navigation")
        settings = nav.get_by_role("link", name="Settings")
        heading = page.get_by_role("heading", name="Settings", exact=True)
        back = page.get_by_role("button", name="Back to work")
        expect(nav.get_by_role("link", name="Plan")).to_have_attribute("aria-current", "page")
        expect(page.get_by_text("Today is", exact=False)).to_be_visible()
        selected_project = page.get_by_role("button", name="Seminar", exact=True)
        selected_project.click()
        expect(page.get_by_label(task["title"], exact=True)).to_be_visible()
        page.get_by_label("Title", exact=True).fill("Keep this task draft")
        page.get_by_role("button", name="Next week").click()
        expect(page.get_by_role("button", name="Next week")).to_be_enabled()
        week = page.locator(".planner-heading p").inner_text()
        day = page.get_by_role("group", name="Selected day").get_by_role("button").last
        day.click()
        expect(day).to_have_attribute("aria-pressed", "true")

        # Trigger the shared link while scrolled without Playwright moving it into view.
        page.evaluate("window.scrollTo(0, 300)")
        offset = page.evaluate("window.scrollY")
        assert offset > 0
        settings.evaluate("link => link.click()")
        expect(heading).to_be_focused()
        assert page.evaluate("window.scrollY") == 0
        assert no_horizontal_overflow(page)
        page.screenshot(path=evidence / "settings-640-light.png")
        back.focus()
        page.keyboard.press("Enter")
        expect(settings).to_be_focused()
        expect(selected_project).to_have_attribute("aria-current", "true")
        expect(page.get_by_label("Title", exact=True)).to_have_value("Keep this task draft")
        expect(page.locator(".planner-heading p")).to_have_text(week)
        expect(day).to_have_attribute("aria-pressed", "true")
        assert page.evaluate("window.scrollY") == offset

        page.get_by_role("button", name="Start tracking", exact=True).click()
        page.get_by_label("Duration (minutes)").fill("20")
        page.get_by_role("button", name="Start countdown").click()
        current = page.get_by_role("region", name="Current session")
        pause = current.get_by_role("button", name="Pause", exact=True)
        expect(pause).to_be_enabled()
        active = http_json("GET", settings_url + "/api/timer")[1]["active_session"]
        settings.click()
        back.click()
        expect(pause).to_be_enabled()
        assert http_json("GET", settings_url + "/api/timer")[1]["active_session"]["id"] == active["id"]
        pause.click()
        resume = current.get_by_role("button", name="Resume", exact=True)
        expect(resume).to_be_enabled()
        paused = http_json("GET", settings_url + "/api/timer")[1]["active_session"]

        for origin in ("Track", "Stats", "Assistant"):
            link = nav.get_by_role("link", name=origin)
            link.click()
            settings.focus()
            page.keyboard.press("Enter")
            expect(heading).to_be_focused()
            expect(page.get_by_role("complementary", name="Active countdown")).to_contain_text("Paused")
            if origin == "Track":
                page.get_by_text("Manage courses (0 followed)").click()
                expect(page.get_by_text("Save a bCourses token to load courses.")).to_be_visible()
            back.click()
            expect(link).to_have_attribute("aria-current", "page")
        expect(page.get_by_role("complementary", name="Active countdown")).to_contain_text(task["title"])
        assert http_json("GET", settings_url + "/api/timer")[1]["active_session"] == paused

        page.emulate_media(color_scheme="dark")
        for width in (1440, 800, 640, 320):
            page.set_viewport_size({"width": width, "height": 900})
            settings.click()
            expect(back).to_be_visible()
            expect(page.get_by_role("link", name="Review assignments")).to_be_visible()
            expect(page.get_by_role("link", name="Open Google")).to_be_visible()
            assert no_horizontal_overflow(page)
            page.screenshot(path=evidence / f"settings-{width}-dark.png")
            page.go_back()
            expect(nav.get_by_role("link", name="Assistant")).to_have_attribute("aria-current", "page")
        page.go_forward()
        expect(heading).to_be_focused()
        page.get_by_role("link", name="Review assignments").click()
        expect(page.get_by_role("region", name="bCourses")).to_be_visible()
        page.go_back()
        page.get_by_role("link", name="Open Google").click()
        expect(page.get_by_role("region", name="Google")).to_be_visible()

        direct = context.new_page()
        direct.goto(settings_url + "/#settings")
        direct.get_by_role("button", name="Back to work").click()
        expect(direct.get_by_role("link", name="Plan", exact=True)).to_have_attribute("aria-current", "page")
        assert errors == []
    finally:
        context.close()


def test_credential_dialogs_retry_and_clear_transient_input(browser, settings_url, evidence):
    expect = playwright_sync.expect
    page = browser.new_page(viewport={"width": 640, "height": 800}, color_scheme="dark")
    token_requests = []
    google_requests = []
    pending_token = []

    def save_token(route):
        token_requests.append(route.request.method)
        if len(token_requests) == 1:
            pending_token.append(route)
        else:
            route.fulfill(json={})

    def save_google(route):
        google_requests.append(route.request.method)
        if len(google_requests) == 1:
            route.fulfill(status=422, json={"error": {"message": "Choose a Desktop app file.", "field": "client_file"}})
        else:
            route.fulfill(json={})

    page.route("**/api/connections/bcourses", save_token)
    page.route("**/api/connections/google", save_google)
    try:
        page.goto(settings_url + "/#settings")
        trigger = page.get_by_role("button", name="Set up or replace bCourses token")
        trigger.focus()
        page.keyboard.press("Enter")
        modal = page.get_by_role("dialog", name="Set up bCourses token")
        token = modal.get_by_label("New bCourses token")
        expect(token).to_be_focused()
        expect(token).to_have_attribute("type", "password")
        page.keyboard.press("Shift+Tab")
        assert not trigger.evaluate("node => node === document.activeElement")
        token.fill("synthetic-token")
        with page.expect_request("**/api/connections/bcourses"):
            token.press("Enter")
        expect(modal.get_by_role("button", name="Cancel")).to_be_disabled()
        expect(modal.get_by_role("status")).to_contain_text("Waiting for BearPlans")
        page.keyboard.press("Escape")
        expect(modal).to_be_visible()
        pending_token[0].fulfill(status=422, json={"error": {"message": "The previous token was kept.", "field": "token"}})
        alert = modal.get_by_role("alert")
        expect(alert).to_have_text("The previous token was kept.")
        expect(token).to_be_focused()
        expect(token).to_have_accessible_description("The previous token was kept.")
        expect(token).to_have_value("synthetic-token")
        token.fill("synthetic-retry")
        token.press("Enter")
        expect(modal).to_have_count(0)
        expect(trigger).to_be_focused()
        expect(page.get_by_text("bCourses accepted your token.", exact=False)).to_be_visible()
        trigger.click()
        expect(token).to_have_value("")
        token.fill("discard-this")
        page.keyboard.press("Escape")
        expect(modal).to_have_count(0)
        expect(trigger).to_be_focused()
        trigger.click()
        expect(token).to_have_value("")
        modal.get_by_role("button", name="Cancel").click()
        assert token_requests == ["PUT", "PUT"]

        google = page.get_by_role("button", name="Set up or replace Google sign-in file")
        google.click()
        modal = page.get_by_role("dialog", name="Set up Google sign-in file")
        file = modal.get_by_label("Google Desktop app JSON file")
        submit = modal.get_by_role("button", name="Save sign-in file")
        file.set_input_files({"name": "oversized.json", "mimeType": "application/json", "buffer": b"x" * 17000})
        submit.click()
        expect(modal.get_by_role("alert")).to_contain_text("16 KB")
        assert not google_requests
        file.set_input_files({"name": "wrong.txt", "mimeType": "text/plain", "buffer": b"{}"})
        submit.click()
        expect(modal.get_by_role("alert")).to_contain_text("downloaded Google Desktop app JSON file")
        assert not google_requests
        file.set_input_files({"name": "web.json", "mimeType": "application/json", "buffer": b'{"web":{}}'})
        submit.click()
        expect(modal.get_by_role("alert")).to_have_text("Choose a Desktop app file.")
        assert file.evaluate("node => node.files.length") == 1
        page.screenshot(path=evidence / "settings-640-dark-file-error.png")
        file.set_input_files({"name": "desktop.json", "mimeType": "application/json", "buffer": b'{"installed":{}}'})
        submit.click()
        expect(modal).to_have_count(0)
        expect(google).to_be_focused()
        expect(page.get_by_text("Google sign-in file saved.", exact=False)).to_be_visible()
        google.click()
        assert file.evaluate("node => node.files.length") == 0
        page.keyboard.press("Escape")
        assert google_requests == ["PUT", "PUT"]
    finally:
        page.close()


def test_saved_bcourses_token_check_and_reviewed_removal(browser, evidence, settings_url, monkeypatch):
    from backend.platform.bcourses import TOKEN_KEY
    from backend.platform.secrets import write_secret

    # Isolate the credential even when this test is run without the guard plugin.
    from tempfile import TemporaryDirectory

    expect = playwright_sync.expect
    page = browser.new_page(viewport={"width": 640, "height": 800}, color_scheme="dark")
    with TemporaryDirectory() as temp, monkeypatch.context() as env:
        env.setenv("BEARPLANS_SECRETS_FILE", f"{temp}/settings.env")
        write_secret(TOKEN_KEY, "synthetic-settings-token")

        def check(route):
            if not failures:
                route.fulfill(status=502, json={"error": {"message": "bCourses is unreachable."}})
            else:
                setup = route.fetch(url=settings_url + "/api/connections", method="GET").json()
                setup["bcourses"].update(checked_at="2026-11-06T12:00:00Z", check_ok=False)
                route.fulfill(json=setup)
            failures.append(True)

        failures = []
        page.route("**/api/connections/bcourses/check", check)
        try:
            page.goto(settings_url + "/#settings")
            check_button = page.get_by_role("button", name="Check saved token")
            check_button.click()
            expect(page.get_by_text("Check could not be confirmed.", exact=False)).to_be_visible()
            expect(page.get_by_text("Last check rejected", exact=False)).to_have_count(0)
            check_button.click()
            expect(page.get_by_text("Last check rejected", exact=False)).to_be_visible()
            expect(page.get_by_text("Token saved", exact=True)).to_be_visible()

            trigger = page.get_by_role("button", name="Remove token…")
            trigger.click()
            modal = page.get_by_role("dialog", name="Remove bCourses token?")
            keep = modal.get_by_role("button", name="Keep token")
            expect(keep).to_be_focused()
            expect(modal).to_contain_text("cached assignments and tasks you added will stay")
            page.screenshot(path=evidence / "settings-bcourses-remove-640-dark.png")
            page.keyboard.press("Escape")
            expect(modal).to_have_count(0)
            expect(trigger).to_be_focused()
            assert http_json("GET", settings_url + "/api/connections")[1]["bcourses"]["set"]

            trigger.click()
            keep.click()
            expect(trigger).to_be_focused()
            trigger.click()
            page.route("**/api/connections/bcourses", lambda route: route.fulfill(
                status=503, json={"error": {"message": "The token was not removed."}}
            ), times=1)
            confirm = modal.get_by_role("button", name="Remove token", exact=True)
            confirm.click()
            expect(modal.get_by_role("alert")).to_contain_text("Removal could not be confirmed")
            confirm.click()
            expect(modal).to_have_count(0)
            expect(page.get_by_text("bCourses token removed from BearPlans.")).to_be_visible()
            expect(page.get_by_role("button", name="Set up or replace bCourses token")).to_be_focused()
            assert no_horizontal_overflow(page)
            page.reload()
            expect(check_button).to_have_count(0)
            assert not http_json("GET", settings_url + "/api/connections")[1]["bcourses"]["set"]
        finally:
            page.close()


@pytest.mark.parametrize("width,height", [(640, 800), (800, 900), (1440, 900)])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_settings_layout_and_keyboard_dialog_at_review_sizes(browser, settings_url, evidence, width, height, theme):
    expect = playwright_sync.expect
    page = browser.new_page(viewport={"width": width, "height": height}, color_scheme=theme)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(settings_url + "/#settings")
        heading = page.get_by_role("heading", name="Settings", exact=True)
        expect(heading).to_be_focused()
        expect(page.get_by_role("link", name="Review assignments")).to_be_visible()
        expect(page.get_by_role("link", name="Open Google")).to_be_visible()
        assert no_horizontal_overflow(page)
        page.screenshot(path=evidence / f"settings-review-{width}-{theme}.png", full_page=True)

        trigger = page.get_by_role("button", name="Set up or replace bCourses token")
        trigger.focus()
        page.keyboard.press("Enter")
        dialog = page.get_by_role("dialog", name="Set up bCourses token")
        field = dialog.get_by_label("New bCourses token")
        expect(field).to_be_focused()
        assert no_horizontal_overflow(page)
        page.screenshot(path=evidence / f"settings-dialog-{width}-{theme}.png")
        page.keyboard.press("Escape")
        expect(dialog).to_have_count(0)
        expect(trigger).to_be_focused()
        assert errors == []
    finally:
        page.close()


def test_credential_error_exposes_name_and_description_in_accessibility_tree(browser, settings_url):
    page = browser.new_page(viewport={"width": 640, "height": 800})
    page.route("**/api/connections/bcourses", lambda route: route.fulfill(
        status=422, json={"error": {"message": "The previous token was kept.", "field": "token"}}
    ))
    try:
        page.goto(settings_url + "/#settings")
        page.get_by_role("button", name="Set up or replace bCourses token").click()
        dialog = page.get_by_role("dialog", name="Set up bCourses token")
        field = dialog.get_by_label("New bCourses token")
        field.fill("synthetic-token")
        dialog.get_by_role("button", name="Check and save").click()
        playwright_sync.expect(field).to_have_accessible_description("The previous token was kept.")
        playwright_sync.expect(field).to_be_focused()

        cdp = page.context.new_cdp_session(page)
        tree = cdp.send("Accessibility.getFullAXTree")["nodes"]
        controls = [node for node in tree if node.get("role", {}).get("value") == "textbox"
                    and node.get("name", {}).get("value") == "New bCourses token"]
        assert len(controls) == 1
        assert controls[0]["description"]["value"] == "The previous token was kept."
        assert any(node.get("role", {}).get("value") == "dialog"
                   and node.get("name", {}).get("value") == "Set up bCourses token" for node in tree)
        assert any(node.get("role", {}).get("value") == "alert" for node in tree)
    finally:
        page.close()


def test_settings_at_actual_chrome_200_percent_zoom(settings_url, tmp_path, evidence):
    expect = playwright_sync.expect
    with playwright_sync.sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(tmp_path / "chrome-profile"), channel="chrome", headless=True,
            viewport={"width": 640, "height": 800}, device_scale_factor=1,
        )
        try:
            settings = context.new_page()
            settings.goto("chrome://settings/appearance")
            zoom = settings.locator("select").filter(has_text="200%")
            zoom.select_option(label="200%")
            expect(zoom).to_have_value("2")
            page = context.new_page()
            page.goto(settings_url + "/#settings")
            assert page.evaluate("window.devicePixelRatio") == 2
            assert page.evaluate("window.innerWidth") == 320
            expect(page.get_by_role("link", name="Review assignments")).to_be_visible()
            expect(page.get_by_role("link", name="Open Google")).to_be_visible()
            assert no_horizontal_overflow(page)
            page.screenshot(path=evidence / "settings-200-percent.png", full_page=True)
            trigger = page.get_by_role("button", name="Set up or replace bCourses token")
            trigger.click()
            dialog = page.get_by_role("dialog", name="Set up bCourses token")
            expect(dialog.get_by_label("New bCourses token")).to_be_focused()
            cancel = dialog.get_by_role("button", name="Cancel")
            expect(cancel).to_be_visible()
            box = dialog.bounding_box()
            assert box is not None and box["y"] >= 0 and box["y"] + box["height"] <= 400
            cancel.scroll_into_view_if_needed()
            expect(cancel).to_be_in_viewport()
            assert no_horizontal_overflow(page)
            page.screenshot(path=evidence / "settings-dialog-200-percent.png")
            page.keyboard.press("Escape")
            expect(trigger).to_be_focused()
        finally:
            context.close()
