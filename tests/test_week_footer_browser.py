"""End Week remains after the board and cancel keeps the week open."""
import pytest
from tests.conftest import Service, free_port
from tests.test_e2e_browser import browser, evidence, no_horizontal_overflow, playwright_sync

pytestmark = pytest.mark.e2e

@pytest.mark.parametrize("width,theme", [(375, "dark"), (640, "light"), (1440, "dark")])
def test_week_footer_and_cancel(browser, evidence, tmp_path, width, theme):
    expect = playwright_sync.expect
    service = Service(tmp_path / f"week-footer-{width}", free_port()).start()
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=theme)
    try:
        page.goto(service.url)
        page.get_by_role("navigation", name="Plan views").get_by_role("button", name="Week").click()
        board = page.locator(".week-board")
        button = page.get_by_role("button", name="End Week", exact=True)
        expect(button).to_be_visible()
        assert board.evaluate("(board, button) => Boolean(board.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING)", button.element_handle())
        assert no_horizontal_overflow(page)
        button.scroll_into_view_if_needed()
        page.screenshot(path=str(evidence / f"week-footer-{width}-{theme}.png"))
        button.focus()
        page.keyboard.press("Enter")
        preview = page.get_by_role("region", name="End week preview")
        expect(preview).to_be_visible()
        preview.get_by_role("button", name="Cancel", exact=True).click()
        expect(preview).to_have_count(0)
        expect(button).to_be_focused()
        expect(page.get_by_text("Open week", exact=True)).to_be_visible()
    finally:
        page.close()
        service.stop()
