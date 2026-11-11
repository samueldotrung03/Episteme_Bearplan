"""Compact completed project leaves using disposable local records."""
import pytest
from tests.conftest import Service, free_port, http_json
from tests.test_e2e_browser import browser, evidence, no_horizontal_overflow, playwright_sync

pytestmark = pytest.mark.e2e

@pytest.mark.parametrize("width,theme", [(375, "dark"), (640, "light"), (1440, "dark")])
def test_reopen_compact_task_by_keyboard(browser, evidence, tmp_path, width, theme):
    expect = playwright_sync.expect
    service = Service(tmp_path / f"compact-{width}", free_port()).start()
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=theme)
    try:
        _, task = http_json("POST", service.url + "/api/tasks", {"title": "Review the source", "notes": "Keep this detail", "estimate_minutes": 30})
        http_json("PUT", service.url + f"/api/tasks/{task['id']}/completion", {"complete": True})
        page.goto(service.url)
        page.get_by_role("navigation", name="Plan views").get_by_role("button", name="Projects").click()
        checkbox = page.get_by_label("Review the source", exact=True)
        row = checkbox.locator("xpath=ancestor::div[contains(@class, 'task-row')]")
        expect(checkbox).to_be_checked()
        expect(row).not_to_contain_text("Keep this detail")
        expect(row.get_by_role("button")).to_have_count(0)
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / f"compact-task-{width}-{theme}.png"))
        checkbox.focus()
        page.keyboard.press("Space")
        expect(checkbox).not_to_be_checked()
        expect(checkbox).to_be_focused()
        expect(row).to_contain_text("Keep this detail")
        expect(row.get_by_role("button", name="Edit")).to_be_visible()
    finally:
        page.close()
        service.stop()
