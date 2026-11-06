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
            back.click()
            expect(link).to_have_attribute("aria-current", "page")
        expect(page.get_by_role("complementary", name="Active countdown")).to_contain_text(task["title"])
        assert http_json("GET", settings_url + "/api/timer")[1]["active_session"] == paused

        page.emulate_media(color_scheme="dark")
        for width in (1440, 800, 640, 320):
            page.set_viewport_size({"width": width, "height": 900})
            settings.click()
            expect(back).to_be_visible()
            expect(page.get_by_role("link", name="Open bCourses")).to_be_visible()
            expect(page.get_by_role("link", name="Open Google")).to_be_visible()
            assert no_horizontal_overflow(page)
            page.screenshot(path=evidence / f"settings-{width}-dark.png")
            page.go_back()
            expect(nav.get_by_role("link", name="Assistant")).to_have_attribute("aria-current", "page")
        page.go_forward()
        expect(heading).to_be_focused()
        page.get_by_role("link", name="Open bCourses").click()
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
