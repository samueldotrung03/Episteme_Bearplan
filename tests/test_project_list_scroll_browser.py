"""Crowded project task list remains reachable using disposable data."""
import pytest
from tests.conftest import Service, free_port, http_json
from tests.test_e2e_browser import browser, evidence, no_horizontal_overflow, playwright_sync

pytestmark = pytest.mark.e2e

@pytest.mark.parametrize("width,theme", [(375, "dark"), (640, "light"), (1440, "dark")])
def test_crowded_project_scroll_and_edit(browser, evidence, tmp_path, width, theme):
    expect = playwright_sync.expect
    service = Service(tmp_path / f"project-scroll-{width}", free_port()).start()
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=theme)
    try:
        for index in range(15):
            http_json("POST", service.url + "/api/tasks", {"title": f"Task {index:02d} with a long descriptive name"})
        page.goto(service.url)
        page.get_by_role("navigation", name="Plan views").get_by_role("button", name="Projects").click()
        task_list = page.get_by_role("list", name="Tasks in Inbox")
        assert task_list.evaluate("element => element.scrollHeight > element.clientHeight")
        last = task_list.get_by_text("Task 14 with a long descriptive name", exact=True)
        last.scroll_into_view_if_needed()
        expect(last).to_be_visible()
        assert task_list.evaluate("element => element.scrollTop > 0")
        row = task_list.locator("li.task").filter(has_text="Task 14 with a long descriptive name")
        edit = row.get_by_role("button", name="Edit", exact=True)
        edit.focus()
        page.keyboard.press("Enter")
        title = row.get_by_label("Title", exact=True)
        title.fill("Retained unsaved edit")
        page.get_by_role("navigation", name="Plan views").get_by_role("button", name="Week").click()
        page.get_by_role("navigation", name="Plan views").get_by_role("button", name="Projects").click()
        expect(title).to_have_value("Retained unsaved edit")
        expect(title).to_be_visible()
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / f"project-scroll-{width}-{theme}.png"))
    finally:
        page.close()
        service.stop()
