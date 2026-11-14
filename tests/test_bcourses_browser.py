"""bCourses tab in real Chrome: choose courses → review → Add → due-date change → narrow layout.

The app runs in-process (uvicorn thread) with a fake bCourses client, so no
network or real token is involved; Add/Refresh go through the real routes and DB.
"""
from __future__ import annotations

import threading
import time

import pytest
import uvicorn

from backend.app import create_app
from backend.domain.tasks import list_tasks
from backend.platform.bcourses import BCoursesUnavailable
from backend.platform.paths import FRONTEND_DIST
from backend.storage.db import open_database
from tests.conftest import free_port, http_json
from tests.test_bcourses import FakeClient
from tests.test_e2e_browser import browser, evidence, no_horizontal_overflow, playwright_sync

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(not (FRONTEND_DIST / "index.html").is_file(), reason="frontend not built")]


@pytest.fixture
def served(tmp_path, monkeypatch):
    monkeypatch.setenv("BEARPLANS_TIMEZONE", "America/Los_Angeles")
    db = open_database(tmp_path / "bearplans.sqlite3")
    fake = FakeClient()
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(create_app(db, FRONTEND_DIST, bcourses_client=fake),
                                           host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}", db, fake
    server.should_exit = True
    thread.join(10)


def test_choose_courses_add_assignment_and_review_due_change(browser, evidence, served):
    expect = playwright_sync.expect
    url, db, fake = served
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="en-US", timezone_id="America/Los_Angeles")
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    fake.by_course["1"][0]["due_at"] = "2099-11-07T07:59:00Z"
    fake.course_list.extend(
        {"id": str(number), "name": f"Seminar {number} · A long course title for the narrow Settings view"}
        for number in range(3, 13)
    )
    try:
        page.goto(url + "/#bcourses")
        tab = page.get_by_role("region", name="bCourses")
        expect(tab.get_by_text("Choose courses in Settings", exact=False)).to_be_visible()
        assert fake.calls == []
        tab.get_by_role("link", name="Manage courses in Settings").click()
        settings = page.get_by_role("region", name="Settings")
        settings.get_by_text("Manage courses (0 followed)").click()
        expect(settings.get_by_text("Refresh to load your bCourses course list.")).to_be_visible()
        assert fake.calls == []
        page.set_viewport_size({"width": 640, "height": 850})
        page.emulate_media(color_scheme="dark")
        settings.get_by_role("button", name="Refresh", exact=True).click()
        course = settings.get_by_role("checkbox", name="MATH 54 - Linear Algebra")
        course.check()
        assert no_horizontal_overflow(page)
        courses = settings.get_by_role("group", name="Choose the courses whose assignments you want to see")
        assert courses.evaluate("node => node.scrollHeight > node.clientHeight")
        last_course = courses.get_by_role("checkbox").last
        last_course.focus()
        expect(last_course).to_be_in_viewport()
        page.screenshot(path=str(evidence / "bcourses-01-choose.png"), full_page=True)
        fake.fail = BCoursesUnavailable("bcourses_unreachable", "Cannot reach bCourses.")
        settings.get_by_role("button", name="Save courses").click()
        expect(settings.get_by_role("alert")).to_contain_text("Your course selection is saved")
        expect(course).to_be_checked()
        assert list_tasks(db) == []
        fake.fail = None
        settings.get_by_role("button", name="Refresh", exact=True).click()
        expect(settings.get_by_role("status")).to_contain_text("Updated from bCourses.")
        settings.get_by_role("link", name="Review assignments").click()
        expect(tab.get_by_role("heading", name="bCourses", exact=True)).to_be_focused()

        upcoming = tab.get_by_role("list", name="Upcoming assignments")
        expect(upcoming.get_by_role("listitem")).to_have_count(1)
        expect(upcoming).to_contain_text("Problem set 5")
        expect(upcoming).to_contain_text("Due Fri, Nov 6")
        expect(upcoming.get_by_role("link", name="Open in bCourses")).to_have_attribute("href", fake.by_course["1"][0]["html_url"])
        expect(tab.get_by_role("list", name="Assignments with no due date").get_by_role("listitem")).to_have_count(2)
        assert [t.title for t in list_tasks(db)] == []  # Nothing imported before Add.
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / "bcourses-02-review.png"), full_page=True)

        tab.get_by_role("button", name="Dismiss “Reading reflection”").click()
        tab.get_by_text("Dismissed (1)", exact=True).click()
        tab.get_by_role("list", name="Dismissed assignments").get_by_role("button", name="Restore").click()
        expect(tab.get_by_role("button", name="Dismiss “Reading reflection”")).to_be_visible()
        tab.get_by_role("button", name="Add “Problem set 5” as a task").click()
        expect(tab.get_by_role("status")).to_contain_text("Added “Problem set 5” to MATH 54 - Linear Algebra, due Fri, Nov 6")
        tasks = [t for t in list_tasks(db) if t.title == "Problem set 5"]
        assert len(tasks) == 1 and str(tasks[0].deadline) == "2099-11-06"
        status, replay = http_json("POST", url + "/api/bcourses/assignments/11/add")
        assert status == 200 and replay["task"]["id"] == tasks[0].id
        page.get_by_role("link", name="Plan", exact=True).click()
        page.get_by_role("navigation", name="Plan views").get_by_role("button", name="Projects", exact=True).click()
        expect(page.get_by_role("button", name="MATH 54 - Linear Algebra", exact=True)).to_be_visible()

        page.evaluate("window.location.hash = '#bcourses'")  # bCourses moved into Settings (Atelier app bar)
        fake.by_course["1"][0]["due_at"] = "2099-11-10T07:59:00Z"
        tab.get_by_role("button", name="Refresh", exact=True).click()
        changed = tab.get_by_role("list", name="Due date changed")
        expect(changed).to_contain_text("Your task: Fri, Nov 6 → bCourses: Mon, Nov 9")
        page.screenshot(path=str(evidence / "bcourses-03-due-changed.png"), full_page=True)
        changed.get_by_role("button", name="Use new due date").click()
        expect(tab.get_by_role("status")).to_contain_text("Updated the due date")
        expect(tab.get_by_role("list", name="Due date changed")).to_have_count(0)
        assert str(next(t for t in list_tasks(db) if t.title == "Problem set 5").deadline) == "2099-11-09"

        page.set_viewport_size({"width": 375, "height": 850})
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / "bcourses-04-narrow.png"), full_page=True)
        tab.get_by_role("link", name="Manage courses in Settings").click()
        course.uncheck()
        settings.get_by_role("button", name="Save courses").click()
        expect(settings.get_by_text("Manage courses (0 followed)")).to_be_visible()
        page.reload()
        settings.get_by_text("Manage courses (0 followed)").click()
        expect(course).to_be_enabled()
        expect(course).not_to_be_checked()
        assert [task.id for task in list_tasks(db)] == [tasks[0].id]
        assert errors == []
    finally:
        page.close()
