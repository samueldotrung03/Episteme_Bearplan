"""The Today projection uses the real local service and task records."""
import pytest
from tests.conftest import Service, free_port, http_json
from tests.test_e2e_browser import browser, evidence, no_horizontal_overflow, playwright_sync

pytestmark = pytest.mark.e2e

@pytest.mark.parametrize("width,theme", [(375, "dark"), (640, "light"), (1440, "dark")])
def test_today_completion_reopen_and_focus(browser, evidence, tmp_path, width, theme):
    expect = playwright_sync.expect
    service = Service(tmp_path / f"today-{width}", free_port()).start()
    context = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=theme)
    try:
        _, project = http_json("POST", service.url + "/api/projects", {"name": "Seminar"})
        _, task = http_json("POST", service.url + "/api/tasks", {"title": "Read the primary source", "project_id": project["id"]})
        _, planning = http_json("GET", service.url + "/api/planning")
        http_json("POST", service.url + "/api/placements", {"task_id": task["id"], "planned_date": planning["today"]})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(service.url)
        nav = page.get_by_role("navigation", name="Main navigation")
        for name in ("Plan", "Track", "Stats", "Assistant", "bCourses", "Google", "Settings"):
            expect(nav.get_by_role("link", name=name, exact=True)).to_be_visible()
        for icon in (page.locator(".app-brand img"), nav.get_by_role("link", name="Settings").locator("img")):
            assert icon.evaluate("image => image.complete && image.naturalWidth === 20 && image.naturalHeight === 20")
            assert icon.bounding_box()["width"] == 20 and icon.bounding_box()["height"] == 20
        today = page.get_by_role("region", name="Today")
        checkbox = today.get_by_role("checkbox", name="Read the primary source — Seminar")
        expect(checkbox).to_be_visible()
        expect(today.get_by_text("Seminar", exact=True)).to_be_visible()
        streak = today.get_by_role("region", name="Saved focus streak")
        expect(streak.get_by_text("0-day streak")).to_be_visible()
        icon = streak.locator("img")
        assert icon.evaluate("image => image.complete && image.naturalWidth === 24 && image.naturalHeight === 24")
        assert icon.bounding_box()["width"] == 24 and icon.bounding_box()["height"] == 24
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / f"today-{width}-{theme}.png"), full_page=True)
        checkbox.focus()
        page.keyboard.press("Space")
        completed = today.get_by_role("button", name="Completed · 1")
        expect(completed).to_be_focused()
        completed.click()
        done = today.get_by_role("checkbox", name="Read the primary source — Seminar")
        expect(done).to_be_checked()
        done.focus()
        page.keyboard.press("Space")
        expect(checkbox).to_be_focused()
        expect(checkbox).not_to_be_checked()
        assert not errors
    finally:
        context.close()
        service.stop()


def test_today_many_tasks_remain_reachable_and_start_correct_task(browser, tmp_path):
    expect = playwright_sync.expect
    service = Service(tmp_path / "today-many", free_port()).start()
    context = browser.new_context(viewport={"width": 640, "height": 800})
    try:
        _, planning = http_json("GET", service.url + "/api/planning")
        last = None
        for index in range(7):
            _, task = http_json("POST", service.url + "/api/tasks", {"title": f"Sample task {index + 1}"})
            http_json("POST", service.url + "/api/placements", {"task_id": task["id"], "planned_date": planning["today"]})
            last = task
        page = context.new_page()
        page.goto(service.url)
        today = page.get_by_role("region", name="Today")
        expect(today.get_by_text("7 unfinished · 0 complete")).to_be_visible()
        start = today.get_by_role("button", name="Start Sample task 7")
        start.scroll_into_view_if_needed()
        expect(start).to_be_visible()
        start.click()
        expect(page.get_by_label("Task to track", exact=True)).to_have_value(last["id"])
        assert no_horizontal_overflow(page)
    finally:
        context.close()
        service.stop()
