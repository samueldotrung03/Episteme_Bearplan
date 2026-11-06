"""Google tab and calendar events in real Chrome, with fake Google clients.

Flow: connected tab → choose calendars → event shown beside its day → Add as task →
give it a start time → sync puts it in the BearPlans calendar with a 30-minute
reminder → a tick made in Google appears without reloading → narrow layout.
No network or real token is involved.
"""
from __future__ import annotations

import threading
import time
from datetime import date

import pytest
import uvicorn

from backend.app import create_app
from backend.domain.tasks import list_tasks
from backend.platform.google import GoogleUnavailable
from backend.platform.paths import FRONTEND_DIST
from backend.storage.db import open_database
from tests.conftest import free_port
from tests.test_e2e_browser import browser, evidence, no_horizontal_overflow, playwright_sync
from tests.test_google_calendar import FakeCalendar
from tests.test_google_controls import _signed_in
from tests.test_google_tasks import FakeTasks

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(not (FRONTEND_DIST / "index.html").is_file(), reason="frontend not built")]

TODAY = date.today().isoformat()


class FakeGoogleCalendar(FakeCalendar):
    """Writes like FakeCalendar; reads the user's calendars like Google's calendarList."""

    def __init__(self) -> None:
        super().__init__()
        self.lock = threading.Lock()
        self.fail_event_read = False
        self.user_calendars = [{"id": "me@example.com", "summary": "Me", "primary": True, "backgroundColor": "#9fc6e7"},
                               {"id": "club@group", "summary": "Climbing club"}]
        self.user_events = {"me@example.com": [{
            "id": "oh", "summary": "Office hours", "location": "Soda 283",
            "start": {"dateTime": f"{TODAY}T23:00:00-08:00"}, "end": {"dateTime": f"{TODAY}T23:45:00-08:00"}}]}

    def calendar_list(self):
        return self.user_calendars

    def list_events(self, calendar_id, time_min, time_max):
        if self.fail_event_read:
            raise GoogleUnavailable("google_unreachable", "Could not read Google events.")
        return self.user_events.get(calendar_id, [])


@pytest.fixture
def served(tmp_path, monkeypatch):
    monkeypatch.setenv("BEARPLANS_TIMEZONE", "America/Los_Angeles")
    _signed_in()
    db = open_database(tmp_path / "bearplans.sqlite3")
    tasks, calendar = FakeTasks(), FakeGoogleCalendar()
    port = free_port()
    app = create_app(db, FRONTEND_DIST, google_tasks_client=tasks, google_calendar_client=calendar)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}", db, tasks, calendar
    server.should_exit = True
    thread.join(10)


def test_calendars_events_start_time_and_ticks_from_google(browser, evidence, served):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    if datetime.now(ZoneInfo("America/Los_Angeles")).hour >= 23:
        pytest.skip("the test plans an event at 23:15 today; too late to be upcoming")
    expect = playwright_sync.expect
    url, db, tasks, calendar = served
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="en-US", timezone_id="America/Los_Angeles")
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(url + "/#google")
        tab = page.get_by_role("region", name="Google")
        expect(tab.get_by_text("Google sign-in is saved.")).to_be_visible()
        tab.get_by_role("checkbox", name="Me · main calendar").check()
        page.screenshot(path=str(evidence / "google-01-calendars.png"), full_page=True)
        tab.get_by_role("button", name="Save calendars").click()
        expect(tab.get_by_role("status")).to_contain_text("Saved your calendars")

        page.get_by_role("link", name="Plan", exact=True).click()
        events = page.locator(".day-events")
        expect(events).to_have_count(1)
        expect(events.get_by_text("Office hours")).not_to_be_visible()  # closed until opened
        events.get_by_text("From your calendar (1)").click()
        expect(events).to_contain_text("Office hours")
        expect(events).to_contain_text("Me · Soda 283")
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / "google-02-day-event.png"), full_page=True)
        events.get_by_role("button", name="Add as task").click()
        expect(events).to_contain_text("Added as a task")
        card = page.locator(".planned-card", has_text="Office hours")
        expect(card).to_have_count(1)
        [task] = [t for t in list_tasks(db) if t.title == "Office hours"]
        assert task.estimate_minutes == 45 and "Where: Soda 283" in task.notes

        card.get_by_text("Move or remove").click()
        card.get_by_label("Start time on", exact=False).fill("23:15")
        card.get_by_role("button", name="Save time").click()
        expect(page.locator(".planned-card", has_text="Office hours")).to_contain_text("At 11:15 PM")

        page.get_by_role("link", name="Google", exact=True).click()
        tab.get_by_role("button", name="Sync now").click()
        expect(tab.get_by_role("status")).to_contain_text("Google sync finished.")
        expect(tab).to_contain_text("1 upcoming event in the “BearPlans” calendar")
        [event] = calendar.live()
        assert event["summary"] == "Office hours"
        assert event["reminders"] == {"useDefault": False, "overrides": [{"method": "popup", "minutes": 30}]}
        page.screenshot(path=str(evidence / "google-03-synced.png"), full_page=True)

        # Tick it in Google; the open page picks it up when the window regains focus.
        page.get_by_role("link", name="Plan", exact=True).click()
        page.evaluate("window.dispatchEvent(new Event('focus'))")  # learn the current version
        page.wait_for_timeout(300)
        google_task = next(item for items in tasks.items.values() for item in items.values() if item.get("title") == "Office hours")
        google_task["status"] = "completed"
        assert page.request.post(url + "/api/google/tasks/sync").ok
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        expect(page.locator(".planned-card", has_text="Office hours").get_by_role("checkbox")).to_be_checked()

        # A later failure still leaves the completion imported by Google Tasks.
        previous = page.request.get(url + "/api/google").json()["tasks"]["last_success_at"]
        google_task["status"] = "needsAction"
        calendar.fail_event_read = True
        draft = page.get_by_label("Title", exact=True)
        draft.fill("Draft kept during Google sync")
        page.get_by_role("link", name="Settings").click()
        settings = page.get_by_role("region", name="Settings")
        settings.get_by_role("button", name="Pause automatic sync").click()
        once = settings.get_by_role("button", name="Sync once")
        once.click()
        expect(settings.get_by_role("alert")).to_contain_text(
            "Google Tasks and calendar publishing finished, but reading selected calendars did not finish."
        )
        failed = page.request.get(url + "/api/google").json()["tasks"]
        assert failed["paused_at"] and failed["last_success_at"] == previous
        expect(settings.get_by_text("Google sync finished.")).to_have_count(0)
        expect(settings.get_by_text("Last full sync", exact=False)).to_be_visible()
        page.screenshot(path=evidence / "google-partial-sync.png")
        page.get_by_role("button", name="Back to work").click()
        expect(page.locator(".planned-card", has_text="Office hours").get_by_role("checkbox")).not_to_be_checked()
        expect(draft).to_have_value("Draft kept during Google sync")

        calendar.fail_event_read = False
        page.get_by_role("link", name="Settings").click()
        once.click()
        expect(settings.get_by_text("Google sync finished.")).to_be_visible()
        recovered = page.request.get(url + "/api/google").json()["tasks"]
        assert recovered["paused_at"] == failed["paused_at"]
        assert recovered["last_success_at"] > previous and recovered["last_error"] is None
        assert [item["id"] for group in tasks.items.values() for item in group.values()
                if item.get("title") == "Office hours"] == [google_task["id"]]

        page.get_by_role("link", name="Google", exact=True).click()
        tab.get_by_role("checkbox", name="Me · main calendar").uncheck()
        tab.get_by_role("button", name="Save calendars").click()
        expect(tab.get_by_role("status")).to_contain_text("Plan now shows events from your selection")
        page.get_by_role("link", name="Plan", exact=True).click()
        expect(events).to_have_count(0)
        expect(card).to_have_count(1)
        assert [t.id for t in list_tasks(db) if t.title == "Office hours"] == [task.id]
        assert calendar.user_events["me@example.com"][0]["id"] == "oh"
        assert not google_task.get("deleted")

        page.set_viewport_size({"width": 375, "height": 850})
        page.get_by_role("link", name="Google", exact=True).click()
        assert no_horizontal_overflow(page)
        page.screenshot(path=str(evidence / "google-04-narrow.png"), full_page=True)
        assert errors == []
    finally:
        page.close()


def test_settings_pause_sync_once_and_resume(browser, evidence, served):
    expect = playwright_sync.expect
    url, _, _, _ = served
    page = browser.new_page(viewport={"width": 640, "height": 800}, color_scheme="dark")
    try:
        page.goto(url + "/#settings")
        settings = page.get_by_role("region", name="Settings")
        pause = settings.get_by_role("button", name="Pause automatic sync")
        resume = settings.get_by_role("button", name="Resume automatic sync")
        expect(settings.get_by_text("Sign-in saved", exact=True)).to_be_visible()
        pause.click()
        expect(resume).to_be_enabled()
        paused_at = page.request.get(url + "/api/google").json()["tasks"]["paused_at"]
        assert paused_at
        page.reload()
        expect(settings.get_by_text("Automatic sync is paused.")).to_be_visible()
        settings.get_by_role("button", name="Sync once").click()
        expect(settings.get_by_text("Google sync finished.")).to_be_visible()
        assert page.request.get(url + "/api/google").json()["tasks"]["paused_at"] == paused_at
        assert no_horizontal_overflow(page)
        page.screenshot(path=evidence / "settings-640-dark-paused.png")
        resume.click()
        expect(settings.get_by_text("Automatic sync is enabled.")).to_be_visible()
        assert page.request.get(url + "/api/google").json()["tasks"]["paused_at"] is None
    finally:
        page.close()


def test_google_sharing_review_precedes_browser_sign_in(browser, evidence, served):
    expect = playwright_sync.expect
    url, *_ = served
    page = browser.new_page(viewport={"width": 640, "height": 800}, color_scheme="dark")
    attempts = []
    missing_permissions = []
    auth_url = "https://accounts.google.com/o/oauth2/auth?fixture=sharing-review"
    page.add_init_script("window.open = () => null")

    def state(route):
        current = route.fetch().json()
        current.update(connected=False, sign_in_pending=bool(attempts),
                       sign_in_attempt_id="fixture" if attempts else None, missing_permissions=missing_permissions)
        route.fulfill(json=current)

    def connect(route):
        attempts.append(route.request.method)
        route.fulfill(json={"url": auth_url, "attempt_id": "fixture"})

    page.route("**/api/google", state)
    page.route("**/api/google/connect", connect)
    try:
        page.goto(url + "/#settings")
        page.get_by_role("link", name="Open Google").click()
        trigger = page.get_by_role("button", name="Connect Google", exact=True)
        trigger.focus()
        page.keyboard.press("Enter")
        review = page.get_by_role("dialog", name="What BearPlans shares with Google")
        expect(review.get_by_role("button", name="Cancel")).to_be_focused()
        expect(review).to_contain_text("Google calendars you select")
        expect(review).to_contain_text("30-minute reminder")
        expect(review).to_contain_text("including bCourses assignments you added")
        assert not attempts
        assert no_horizontal_overflow(page)
        page.screenshot(path=evidence / "google-sharing-640-dark.png")
        page.keyboard.press("Escape")
        expect(review).to_have_count(0)
        expect(trigger).to_be_focused()
        assert not attempts
        missing_permissions.append("tasks")
        page.reload()
        page.get_by_role("button", name="Reconnect Google", exact=True).click()
        expect(review).to_be_visible()
        assert not attempts
        review.get_by_role("button", name="Continue with Google").click()
        expect(review).to_have_count(0)
        expect(page.get_by_role("link", name="Open Google sign-in")).to_have_attribute("href", auth_url)
        assert attempts == ["POST"]
    finally:
        page.close()
