"""Orchestrator question routing: direct code answers, read-only specialists, fallbacks."""
import asyncio

import pytest

from backend.domain.assistant import AssistantService
from backend.domain.assistant_answers import duration
from backend.domain.calendar import application_today
from backend.domain.planning import create_placement
from backend.domain.projects import create_project
from backend.domain.tasks import create_task, set_task_completion
from tests.test_assistant import FakeProvider, rows


class Recording(FakeProvider):
    async def chat(self, model, messages, tools):
        self.tools = [tool["function"]["name"] for tool in tools]
        return await super().chat(model, messages, tools)


def ask(db, route, prompt):
    provider = Recording(routes=[{"intent": "question", **route}])
    return asyncio.run(AssistantService(db, provider).ask("fixture:local", prompt)), provider


@pytest.fixture
def data(db):
    writing = create_project(db, "Writing")
    history = create_project(db, "History")
    essay = create_task(db, "Essay", project_id=writing.id)
    outline = create_task(db, "Outline", parent_id=essay.id)
    set_task_completion(db, outline.id, True)
    draft = create_task(db, "Draft intro", parent_id=essay.id, deadline="2026-11-20")
    reading = create_task(db, "Reading", project_id=history.id)
    notes = create_task(db, "Chapter 3 notes", parent_id=reading.id)
    create_placement(db, draft.id, application_today()[0])
    return {"draft": draft, "notes": notes, "outline": outline}


def test_duration_is_readable():
    assert [duration(v) for v in (0, 1_500_000, 60_000_000, 60_000_001, 3_900_000_000, 7_200_000_000)] == [
        "0 s", "1.5 s", "1 min", "1 min", "1 h 5 min", "2 h 0 min"]


def test_today_plan_is_answered_directly_without_a_model(db, data):
    before = rows(db)
    reply, provider = ask(db, {"topic": "plan"}, "What is planned today?")
    assert reply["route"]["agents"] == ["router", "direct"] and provider.messages == []
    assert reply["answer"].startswith("Today (") and "Draft intro — Writing / Essay (incomplete, due 2026-11-20)" in reply["answer"]
    assert reply["sources"][0]["tool"] == "get_day_plan" and rows(db) == before
    week, _ = ask(db, {"topic": "plan"}, "Show this week's plan")
    assert week["route"]["agents"] == ["router", "direct"] and week["answer"].startswith("Week of Mon ")


def test_task_lists_and_searches_are_direct(db, data):
    reply, provider = ask(db, {"topic": "tasks"}, "Check the incomplete subtasks")
    assert reply["route"]["agents"] == ["router", "direct"] and provider.messages == []
    assert reply["answer"].startswith("2 incomplete subtasks across all projects:")
    assert reply["sources"][0]["arguments"] == {"status": "incomplete", "level": "subtasks", "order": "deadline"}
    done, _ = ask(db, {"topic": "tasks", "project": "Writing"}, "Which subtasks are done in Writing?")
    assert done["answer"].startswith("1 complete subtask in Writing:") and "Outline" in done["answer"]
    found, _ = ask(db, {"topic": "tasks", "task": "Reading"}, "Find tasks titled Reading")
    assert found["sources"][0]["tool"] == "search_tasks" and "Reading — History" in found["answer"]


def test_all_time_total_is_direct_but_period_totals_go_to_the_time_specialist(db, data):
    total, provider = ask(db, {"topic": "time"}, "How much saved active time do I have in total?")
    assert total["route"]["agents"] == ["router", "direct"] and provider.messages == []
    assert total["answer"].startswith("All-time saved active time: 0 s across 0 saved sessions.")
    week, provider = ask(db, {"topic": "time"}, "How much did I work this week?")
    assert week["route"]["agents"] == ["router", "time_specialist"] and provider.tools == ["search_tasks", "get_time_summary"]


def test_unclear_questions_fall_back_to_specialists_or_the_general_reader(db, data):
    last, provider = ask(db, {"topic": "plan"}, "What was planned this month?")
    assert last["route"]["agents"] == ["router", "plan_specialist"] and provider.tools == ["get_day_plan", "get_week_plan"]
    vague, provider = ask(db, {"topic": "tasks"}, "Anything urgent?")
    assert vague["route"]["agents"] == ["router", "tasks_specialist"] and provider.tools == ["search_tasks", "list_tasks", "get_task"]
    unknown, provider = ask(db, {"topic": "tasks", "project": "Biology"}, "Which subtasks are open in Biology?")
    assert unknown["route"]["agents"] == ["router", "tasks_specialist"]
    other, provider = ask(db, {}, "Summarize everything")
    assert other["route"]["agents"] == ["router", "reader"] and len(provider.tools) == 6
    odd, _ = ask(db, {"topic": "gossip"}, "Tell me")
    assert odd["route"]["agents"] == ["router", "reader"]


def test_router_details_not_in_the_message_are_ignored_for_questions(db, data):
    reply, _ = ask(db, {"topic": "tasks", "task": "Essay", "project": "History"}, "Check the incomplete subtasks")
    assert reply["sources"][0]["arguments"] == {"status": "incomplete", "level": "subtasks", "order": "deadline"}
    dated, _ = ask(db, {"topic": "plan", "date": "Friday"}, "What is planned today?")
    assert dated["answer"].startswith("Today (")


def test_code_reads_project_titles_and_deadlines_from_the_message(db, data):
    done, provider = ask(db, {"topic": "tasks"}, "Which subtasks are done in Writing?")
    assert done["route"]["agents"] == ["router", "direct"] and done["answer"].startswith("1 complete subtask in Writing:")
    found, _ = ask(db, {"topic": "tasks"}, "Find tasks titled Reading and tell me their projects.")
    assert found["sources"][0]["arguments"] == {"query": "Reading"} and found["answer"].startswith("1 task matches “Reading”")
    create_task(db, "Lab report", deadline="2026-11-05")
    due, _ = ask(db, {"topic": "tasks"}, "What is due soonest?")
    assert due["answer"].splitlines()[1].startswith("• Lab report — Inbox (incomplete) — due Thu 2026-11-05")
    assert due["answer"].splitlines()[2].startswith("• Draft intro") and "Essay" not in due["answer"].splitlines()[0]
    scoped, _ = ask(db, {"topic": "plan"}, "What is planned today in Writing?")
    assert scoped["route"]["agents"] == ["router", "plan_specialist"]


def test_list_tasks_deadline_order_is_bounded_and_read_only(db, data):
    from backend.domain.assistant_tools import read_tool
    create_task(db, "Lab report", deadline="2026-11-05")
    before = rows(db)
    listed = read_tool(db, "list_tasks", {"has_deadline": True, "order": "deadline", "status": "any"})
    assert [t["title"] for t in listed["tasks"]] == ["Lab report", "Draft intro"]
    undated = read_tool(db, "list_tasks", {"has_deadline": False, "level": "work_items"})
    assert "Lab report" not in [t["title"] for t in undated["tasks"]] and rows(db) == before


@pytest.fixture
def next_week(db):
    """Two projects; tasks planned and due next week, plus ones that must be left out."""
    from datetime import timedelta
    today = application_today()[0]
    monday = today - timedelta(days=today.weekday()) + timedelta(days=7)
    testing, other = create_project(db, "Testing"), create_project(db, "Other")
    planned = create_task(db, "Test #2", project_id=testing.id)
    create_placement(db, planned.id, monday + timedelta(days=2))
    create_task(db, "Test #1", project_id=testing.id, deadline=monday + timedelta(days=4))
    create_task(db, "Report", project_id=other.id, deadline=monday + timedelta(days=1))
    create_task(db, "Abstract", project_id=other.id, deadline=monday + timedelta(days=1))
    done = create_task(db, "Finished", project_id=other.id, deadline=monday)
    set_task_completion(db, done.id, True)
    create_task(db, "Later", project_id=other.id, deadline=monday + timedelta(days=7))
    create_task(db, "Earlier", project_id=other.id, deadline=monday - timedelta(days=1))
    return monday


@pytest.mark.parametrize("route", [{"topic": "tasks"},
                                   # The user's run: "next week" copied as search words.
                                   {"topic": "tasks", "task": "next week"}])
def test_todos_for_next_week_show_planned_and_due_across_projects(db, next_week, route):
    """User testing, Nov 11 (A-01): this searched for a task titled "next week" in Testing only."""
    from datetime import timedelta
    before = rows(db)
    reply, provider = ask(db, route, "check the todos for next week")
    assert reply["route"]["agents"] == ["router", "direct"] and provider.messages == [] and rows(db) == before
    sunday = next_week + timedelta(days=6)
    lines = reply["answer"].splitlines()
    assert lines[0] == f"Next week ({next_week:%a} {next_week} – {sunday:%a} {sunday}) across all projects:"
    assert lines[1] == "Planned that week (1):" and lines[2].startswith("• Test #2 — Testing (incomplete)")
    assert lines[3] == "Due that week, not yet complete (3):"
    # A-06: earliest deadline first, then title.
    assert [line.split(" — ")[0] for line in lines[4:]] == ["• Abstract", "• Report", "• Test #1"]
    assert {"Finished", "Later", "Earlier"}.isdisjoint(reply["answer"].replace("Planned", "").split())
    due = reply["sources"][1]
    assert due["tool"] == "list_tasks" and due["arguments"]["due_from"] == next_week.isoformat()
    assert due["arguments"]["due_to"] == sunday.isoformat() and "project" not in due["arguments"]


def test_week_todos_limit_to_a_project_only_when_named(db, next_week):
    reply, _ = ask(db, {"topic": "tasks"}, "What is due next week in Other?")
    assert reply["answer"].startswith("Next week (") and " in Other:" in reply["answer"].splitlines()[0]
    assert "Test #2" not in reply["answer"] and "Test #1" not in reply["answer"]
    assert [l.split(" — ")[0] for l in reply["answer"].splitlines() if l.startswith("•")] == ["• Abstract", "• Report"]


def test_due_next_week_routed_as_time_still_lists_tasks_but_time_questions_do_not(db, next_week):
    soonest, _ = ask(db, {"topic": "time"}, "What is due soonest?")  # live router-v9 route (M5 case R8)
    assert soonest["route"]["agents"] == ["router", "direct"] and soonest["answer"].startswith("Upcoming deadlines")
    due, _ = ask(db, {"topic": "time"}, "what is due next week")  # live router-v9 route
    assert due["route"]["agents"] == ["router", "direct"] and "Due that week" in due["answer"]
    time, provider = ask(db, {"topic": "time"}, "How much time did I spend on tasks this week?")
    assert time["route"]["agents"] == ["router", "time_specialist"]


def test_plan_for_next_or_last_week_is_answered_directly(db, next_week):
    nxt, provider = ask(db, {"topic": "plan"}, "What is planned next week?")
    assert nxt["route"]["agents"] == ["router", "direct"] and provider.messages == []
    assert nxt["answer"].startswith(f"Week of {next_week:%a} {next_week}") and "Test #2" in nxt["answer"]
    assert "Due that week" not in nxt["answer"]


def test_remaining_tasks_are_ordered_by_deadline_then_title(db, next_week):
    """A-06: "Check the remained tasks" listed a later deadline first."""
    reply, _ = ask(db, {"topic": "tasks"}, "Check the remained tasks")
    titles = [line.split(" — ")[0][2:] for line in reply["answer"].splitlines()[1:]]
    assert titles == ["Earlier", "Abstract", "Report", "Test #1", "Later", "Test #2"]
