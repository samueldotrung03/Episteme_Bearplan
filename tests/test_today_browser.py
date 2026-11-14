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
        # Atelier app bar: four destinations plus Settings; bCourses and Google live in Settings.
        for name in ("Plan", "Track", "Stats", "Assistant", "Settings"):
            expect(nav.get_by_role("link", name=name, exact=True)).to_be_visible()
        for name in ("bCourses", "Google"):
            expect(nav.get_by_role("link", name=name, exact=True)).to_have_count(0)
        for icon in (page.locator(".app-brand .icon"), nav.get_by_role("link", name="Settings").locator(".icon")):
            box = icon.bounding_box()
            assert box and round(box["width"]) == 20 and round(box["height"]) == 20
        today = page.get_by_role("region", name="Today")
        checkbox = today.get_by_role("checkbox", name="Read the primary source — Seminar")
        expect(checkbox).to_be_visible()
        expect(today.get_by_text("Seminar", exact=True)).to_be_visible()
        streak = today.get_by_role("region", name="Saved focus streak")
        expect(streak.get_by_text("0-day streak")).to_be_visible()
        # Atelier quiet streak: no icon, seven 12 px day dots with today shown as a ring.
        dots = streak.locator(".today-streak-dot")
        expect(dots).to_have_count(7)
        assert all(round(dots.nth(i).bounding_box()["width"]) == 12 for i in range(7))
        expect(streak.locator(".today-streak-dot.today")).to_have_count(1)
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
        # Start is quiet on rows other than the focused one and appears on hover.
        row = today.locator(".today-task", has_text="Sample task 7")
        row.scroll_into_view_if_needed()
        row.hover()
        expect(start).to_be_visible()
        start.click()
        expect(page.get_by_label("Task to track", exact=True)).to_have_value(last["id"])
        assert no_horizontal_overflow(page)
    finally:
        context.close()
        service.stop()

@pytest.mark.parametrize("width,theme", [(375, "dark"), (640, "light"), (1440, "dark")])
def test_plan_views_preserve_draft_and_week(browser, evidence, tmp_path, width, theme):
    expect = playwright_sync.expect
    service = Service(tmp_path / f"plan-views-{width}", free_port()).start()
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=theme)
    try:
        page.goto(service.url)
        nav = page.get_by_role("navigation", name="Plan views")
        today = nav.get_by_role("button", name="Today")
        week = nav.get_by_role("button", name="Week")
        projects = nav.get_by_role("button", name="Projects")
        expect(today).to_have_attribute("aria-pressed", "true")
        expect(page.get_by_role("region", name="Today")).to_be_visible()
        expect(page.locator(".weekly-planner")).to_be_hidden()
        projects.focus()
        page.keyboard.press("Enter")
        page.get_by_role("button", name="+ Add task", exact=True).click()
        title = page.get_by_label("Title", exact=True)
        title.fill("Keep this draft")
        page.get_by_role("button", name="Keep draft while this page is open").click()
        week.click()
        expect(page.get_by_role("region", name="Weekly plan")).to_be_visible()
        heading = page.locator(".week-range")
        previous_week = heading.inner_text()
        page.get_by_role("button", name="Next week").click()
        expect(heading).not_to_have_text(previous_week)
        viewed_week = heading.inner_text()
        today.click()
        expect(page.get_by_role("region", name="Today")).to_be_visible()
        expect(page.locator(".weekly-planner")).to_be_hidden()
        projects.click()
        page.get_by_role("button", name="Continue task draft").click()
        expect(title).to_have_value("Keep this draft")
        page.get_by_role("button", name="Keep draft while this page is open").click()
        week.click()
        expect(heading).to_have_text(viewed_week)
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / f"plan-week-{width}-{theme}.png"))
        assert not page.locator(":focus").evaluate("node => node.closest('[hidden]') !== null")
    finally:
        page.close()
        service.stop()


@pytest.mark.parametrize("width,theme", [(375, "dark"), (1440, "light")])
def test_today_earlier_unfinished_move_to_today(browser, evidence, tmp_path, width, theme):
    """B1 on Today: past-planned unfinished work is listed and can be planned for today."""
    import datetime as dt
    expect = playwright_sync.expect
    service = Service(tmp_path / f"earlier-{width}", free_port()).start()
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=theme)
    try:
        _, project = http_json("POST", service.url + "/api/projects", {"name": "CS 61A"})
        _, planning = http_json("GET", service.url + "/api/planning")
        today = dt.date.fromisoformat(planning["today"])
        for title, offset in (("Finish the lab write-up", 2), ("Email the TA", 9)):
            _, task = http_json("POST", service.url + "/api/tasks", {"title": title, "project_id": project["id"], "estimate_minutes": 30})
            code, _ = http_json("POST", service.url + "/api/placements", {"task_id": task["id"], "planned_date": (today - dt.timedelta(days=offset)).isoformat()})
            assert code < 300
        page.goto(service.url)
        today_view = page.get_by_role("region", name="Today")
        toggle = today_view.get_by_role("button", name="Earlier unfinished · 2")
        expect(toggle).to_be_visible()
        toggle.click()
        earlier = today_view.get_by_role("list", name="Earlier unfinished tasks")
        expect(earlier.get_by_text("Finish the lab write-up")).to_be_visible()
        expect(earlier).to_contain_text("CS 61A · from")
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / f"today-earlier-{width}-{theme}.png"), full_page=True)
        today_view.get_by_role("button", name="Move both to today").click()
        expect(toggle).to_have_count(0)
        expect(today_view.locator(".today-tasks").first).to_contain_text("Finish the lab write-up")
        expect(today_view.locator(".today-tasks").first).to_contain_text("Email the TA")
        expect(today_view.get_by_text("2 unfinished · 0 complete · 1h planned", exact=True)).to_be_visible()
    finally:
        page.close()
        service.stop()
