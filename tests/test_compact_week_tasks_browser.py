"""Completed weekly task rows, with only disposable data."""
import pytest
from tests.conftest import Service, free_port, http_json
from tests.test_e2e_browser import browser, evidence, no_horizontal_overflow, playwright_sync

pytestmark = pytest.mark.e2e

@pytest.mark.parametrize("width,theme", [(375, "dark"), (640, "light"), (1440, "dark")])
def test_compact_week_reopen_failure_retry(browser, evidence, tmp_path, width, theme):
    expect = playwright_sync.expect
    service = Service(tmp_path / f"week-complete-{width}", free_port()).start()
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=theme)
    attempts = []
    try:
        _, task = http_json("POST", service.url + "/api/tasks", {"title": "Read primary source", "deadline": "2099-12-01", "estimate_minutes": 30})
        _, plan = http_json("GET", service.url + "/api/planning")
        http_json("POST", service.url + "/api/placements", {"task_id": task["id"], "planned_date": plan["today"]})
        http_json("PUT", service.url + f"/api/tasks/{task['id']}/completion", {"complete": True})
        def handle(route):
            if route.request.method == "PUT":
                attempts.append(1)
                if len(attempts) == 1:
                    route.fulfill(status=503, json={"error": {"code": "unavailable", "message": "Could not reopen. Try again."}})
                    return
            route.continue_()
        page.route(f"**/api/tasks/{task['id']}/completion", handle)
        page.goto(service.url)
        page.get_by_role("navigation", name="Plan views").get_by_role("button", name="Week").click()
        card = page.locator(".planned-card").filter(has_text="Read primary source")
        checkbox = card.get_by_role("checkbox")
        expect(checkbox).to_be_checked()
        expect(checkbox).to_have_accessible_description("Inbox")
        expect(card.locator(".planned-card-heading")).to_be_hidden()
        expect(card.get_by_text("Due Dec 1, 2099")).to_be_hidden()
        expect(card.get_by_text("Move or remove")).to_be_hidden()
        assert no_horizontal_overflow(page)
        card.scroll_into_view_if_needed()
        page.screenshot(path=str(evidence / f"completed-week-{width}-{theme}.png"))
        checkbox.focus()
        page.keyboard.press("Space")
        expect(card.get_by_role("alert")).to_contain_text("Could not reopen")
        expect(checkbox).to_be_checked()
        expect(checkbox).to_be_focused()
        page.keyboard.press("Space")
        expect(checkbox).not_to_be_checked()
        expect(checkbox).to_be_focused()
        expect(card.get_by_text("Due Dec 1, 2099")).to_be_visible()
        expect(card.get_by_text("Move or remove")).to_be_visible()
        expect(card.get_by_text("30 min estimated")).to_be_visible()
        if width == 640:
            assert card.get_by_text("Due Dec 1, 2099").bounding_box()["y"] == card.get_by_text("30 min estimated").bounding_box()["y"]
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / f"active-week-{width}-{theme}.png"))
    finally:
        page.close()
        service.stop()
