"""Project controls use disposable data and retain failed input."""
import pytest
from tests.conftest import Service, free_port
from tests.test_e2e_browser import browser, evidence, no_horizontal_overflow, playwright_sync

pytestmark = pytest.mark.e2e

@pytest.mark.parametrize("width,theme", [(375, "dark"), (640, "light"), (1440, "dark")])
def test_project_controls_retry_and_focus(browser, evidence, tmp_path, width, theme):
    expect = playwright_sync.expect
    service = Service(tmp_path / f"projects-{width}", free_port()).start()
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=theme)
    requests = []
    def handle(route):
        if route.request.method == "POST":
            requests.append(1)
            if len(requests) == 1:
                route.fulfill(status=503, json={"error": {"code": "unavailable", "message": "Could not save project. Try again."}})
                return
        route.continue_()
    page.route("**/api/projects", handle)
    try:
        page.goto(service.url)
        page.get_by_role("navigation", name="Plan views").get_by_role("button", name="Projects").click()
        section = page.get_by_role("region", name="Projects")
        add = section.get_by_role("button", name="+ Add project", exact=True)
        expect(section.get_by_label("New project")).to_have_count(0)
        expect(add).to_have_attribute("aria-expanded", "false")
        add.focus()
        page.keyboard.press("Enter")
        field = section.get_by_label("New project")
        expect(field).to_be_focused()
        field.fill("Research notes")
        section.get_by_role("button", name="Add project", exact=True).click()
        expect(section.get_by_role("alert")).to_contain_text("Could not save project")
        expect(field).to_have_value("Research notes")
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / f"project-create-error-{width}-{theme}.png"))
        section.get_by_role("button", name="Add project", exact=True).click()
        expect(section.get_by_role("button", name="Research notes", exact=True)).to_have_attribute("aria-current", "true")
        expect(add).to_be_focused()
        add.click()
        field.fill("Discard this draft")
        section.get_by_role("button", name="Cancel", exact=True).click()
        expect(add).to_be_focused()
        expect(section.get_by_label("New project")).to_have_count(0)
        rename = section.get_by_role("button", name="Rename “Research notes”")
        rename.click()
        rename_field = section.get_by_label("Rename “Research notes”")
        expect(rename_field).to_be_focused()
        rename_field.fill("Changed")
        section.get_by_role("button", name="Cancel", exact=True).click()
        expect(rename).to_be_focused()
        expect(section.get_by_role("button", name="Research notes", exact=True)).to_be_visible()
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / f"project-controls-{width}-{theme}.png"))
    finally:
        page.close()
        service.stop()
