"""On-demand task entry and recovery with disposable data."""
import pytest
from tests.conftest import Service, free_port
from tests.test_e2e_browser import browser, evidence, no_horizontal_overflow, playwright_sync

pytestmark = pytest.mark.e2e

@pytest.mark.parametrize("width,theme", [(375, "dark"), (640, "light"), (1440, "dark")])
def test_add_task_retry_cancel_and_focus(browser, evidence, tmp_path, width, theme):
    expect = playwright_sync.expect
    service = Service(tmp_path / f"task-entry-{width}", free_port()).start()
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=theme)
    attempts = []
    def handle(route):
        if route.request.method == "POST":
            attempts.append(1)
            if len(attempts) == 1:
                route.fulfill(status=503, json={"error": {"code": "unavailable", "message": "Could not save task. Try again."}})
                return
        route.continue_()
    page.route("**/api/tasks", handle)
    try:
        page.goto(service.url)
        page.get_by_role("navigation", name="Plan views").get_by_role("button", name="Projects").click()
        add = page.get_by_role("button", name="+ Add task", exact=True)
        expect(page.get_by_label("Title", exact=True)).to_have_count(0)
        add.focus()
        page.keyboard.press("Enter")
        title = page.get_by_label("Title", exact=True)
        expect(title).to_be_focused()
        title.fill("Read the source")
        page.get_by_label("Notes", exact=True).fill("Keep this note")
        page.get_by_role("button", name="Add task", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("Could not save task")
        expect(title).to_have_value("Read the source")
        expect(page.get_by_label("Notes", exact=True)).to_have_value("Keep this note")
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / f"add-task-error-{width}-{theme}.png"))
        page.get_by_role("button", name="Add task", exact=True).click()
        expect(page.get_by_label("Read the source", exact=True)).to_be_visible()
        expect(title).to_have_value("")
        page.get_by_role("button", name="Cancel", exact=True).click()
        expect(add).to_be_focused()
        expect(page.get_by_label("Title", exact=True)).to_have_count(0)
    finally:
        page.close()
        service.stop()
