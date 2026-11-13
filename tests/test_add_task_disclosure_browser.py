"""On-demand task entry and recovery with disposable data."""
import pytest
from tests.conftest import Service, free_port
from tests.test_e2e_browser import browser, evidence, no_horizontal_overflow, playwright_sync

pytestmark = pytest.mark.e2e

def test_escape_does_not_hide_in_flight_save(browser, tmp_path):
    expect = playwright_sync.expect
    service = Service(tmp_path / "task-dialog-busy", free_port()).start()
    page = browser.new_page()
    try:
        page.goto(service.url)
        page.get_by_role("navigation", name="Plan views").get_by_role("button", name="Projects").click()
        page.get_by_role("button", name="+ Add task", exact=True).click()
        page.get_by_label("Title", exact=True).fill("Save in progress")
        page.evaluate("""() => {
          const original = window.fetch;
          window.fetch = (input, init) => String(input) === '/api/task-captures'
            ? new Promise(() => {}) : original(input, init);
        }""")
        page.get_by_role("button", name="Add task", exact=True).click()
        expect(page.get_by_role("button", name="Saving…")).to_be_disabled()
        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog", name="New task")).to_be_visible()
    finally:
        page.close()
        service.stop()

@pytest.mark.parametrize("width,theme", [(640, "light"), (800, "light"), (1440, "light"), (640, "dark"), (800, "dark"), (1440, "dark")])
def test_task_dialog_keeps_draft_and_traps_keyboard(browser, evidence, tmp_path, width, theme):
    expect = playwright_sync.expect
    service = Service(tmp_path / f"task-dialog-{width}-{theme}", free_port()).start()
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=theme)
    try:
        page.goto(service.url)
        page.get_by_role("navigation", name="Plan views").get_by_role("button", name="Projects").click()
        add = page.get_by_role("button", name="+ Add task", exact=True)
        add.click()
        dialog = page.get_by_role("dialog", name="New task")
        title = dialog.get_by_label("Title", exact=True)
        expect(title).to_be_focused()
        title.fill("Retained draft")
        page.screenshot(path=str(evidence / f"task-dialog-{width}-{theme}.png"))
        assert no_horizontal_overflow(page)
        for _ in range(18):
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement === document.body || !!document.activeElement.closest('dialog[open]')")
        page.keyboard.press("Escape")
        expect(dialog).not_to_be_visible()
        resume = page.get_by_role("button", name="Continue task draft")
        expect(resume).to_be_focused()
        resume.click()
        expect(dialog.get_by_label("Title", exact=True)).to_have_value("Retained draft")
        dialog.get_by_role("button", name="Cancel", exact=True).click()
        expect(add).to_be_focused()
    finally:
        page.close()
        service.stop()

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
    page.route("**/api/task-captures", handle)
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
        page.keyboard.press("Escape")
        page.get_by_role("button", name="Continue task draft").click()
        expect(page.get_by_label("Title", exact=True)).to_have_value("Read the source")
        page.get_by_role("button", name="Check save status", exact=True).click()
        expect(page.get_by_label("Read the source", exact=True)).to_be_visible()
        expect(add).to_be_focused()
        add.click()
        expect(title).to_have_value("")
        page.get_by_role("button", name="Cancel", exact=True).click()
        expect(add).to_be_focused()
        expect(page.get_by_label("Title", exact=True)).to_have_count(0)
    finally:
        page.close()
        service.stop()
