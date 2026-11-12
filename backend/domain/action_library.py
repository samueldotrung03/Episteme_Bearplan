"""Action library and sufficiency gate for assistant change requests.

The router agent only classifies a request and copies details the user stated.
This module decides, without a model, which tool an intent uses, what that tool
needs, and whether the gathered details are sufficient. Names are resolved to
exact records here; anything missing or ambiguous becomes a question or a choice
for the user, never a guess. Only a sufficient request reaches propose_action,
and only the user's Apply changes data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from backend.domain.assistant_actions import propose_action
from backend.domain.errors import InvalidInput
from backend.domain.projects import list_projects
from backend.domain.tasks import Task, list_tasks
from backend.domain.timer import TimerService
from backend.storage.db import Database

ActionIntent = Literal["create_task", "update_task", "assign_task_date", "complete_task",
                       "start_timer", "pause_timer", "resume_timer", "finish_timer", "carry_over_week"]
MAX_CLARIFICATION_ROUNDS = 4
MAX_CHOICES = 8
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


@dataclass(frozen=True)
class ActionSpec:
    tool: str
    description: str
    required: tuple[str, ...]
    optional: tuple[str, ...] = ()


# The library: each change intent, the one tool it may use and the information it needs.
LIBRARY: dict[str, ActionSpec] = {
    "create_task": ActionSpec("create_task", "Create a task or subtask", ("title",),
                              ("project", "parent", "deadline", "estimate_minutes", "notes")),
    "update_task": ActionSpec("update_task", "Edit a task's title, notes, deadline or estimate", ("task", "change"),
                              ("title", "notes", "deadline", "estimate_minutes")),
    "assign_task_date": ActionSpec("assign_task_date", "Plan a task on a date", ("task", "date")),
    "complete_task": ActionSpec("complete_task", "Mark a task complete or reopen it", ("task",), ("complete",)),
    "start_timer": ActionSpec("start_timer", "Start a countdown on a task", ("task", "duration_minutes")),
    "pause_timer": ActionSpec("pause_timer", "Pause the running countdown", ()),
    "resume_timer": ActionSpec("resume_timer", "Resume the paused countdown", ()),
    "finish_timer": ActionSpec("finish_timer", "Finish and save the current countdown", ()),
    # Week defaults to the current one; "last week" or a stated date picks another.
    "carry_over_week": ActionSpec("carry_over_week", "Carry a closed week's unfinished work to the same weekday next week",
                                  (), ("date",)),
}

QUESTIONS = {
    "title": "What should the new task be called?",
    "task": "Which task do you mean? Give its title.",
    "change": "What should change: the title, notes, deadline or estimate?",
    "date": "Which date should it be planned on? For example 2026-11-03 or “next Tuesday”.",
    "duration_minutes": "How many minutes should the countdown run (1–180)?",
}


class Slots(BaseModel):
    """Details gathered so far. Text fields hold the user's own words until resolved."""
    model_config = ConfigDict(extra="forbid", strict=True)
    task: str | None = Field(default=None, max_length=200)
    task_id: str | None = Field(default=None, max_length=100)
    task_label: str | None = Field(default=None, max_length=400)
    project: str | None = Field(default=None, max_length=100)
    project_id: str | None = Field(default=None, max_length=100)
    parent: str | None = Field(default=None, max_length=200)
    parent_id: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)
    # The user's own day words until resolved by parse_day, then YYYY-MM-DD.
    deadline: str | None = Field(default=None, max_length=40)
    date: str | None = Field(default=None, max_length=40)
    estimate_minutes: StrictInt | None = None
    duration_minutes: StrictInt | None = None
    complete: StrictBool | None = None


class Pending(BaseModel):
    """Clarification state the browser returns verbatim; revalidated on every turn."""
    model_config = ConfigDict(extra="forbid", strict=True)
    intent: ActionIntent
    slots: Slots = Field(default_factory=Slots)
    round: StrictInt = Field(default=1, ge=1, le=MAX_CLARIFICATION_ROUNDS)


class Choice(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    slot: Literal["task_id", "project_id", "parent_id"]
    value: str = Field(min_length=1, max_length=100)


def merge(pending: Pending | None, intent: ActionIntent, extracted: Slots) -> Pending:
    """Continue a pending request with newly stated details, or start a new one."""
    if pending is None or pending.intent != intent:
        return Pending(intent=intent, slots=extracted)
    values = pending.slots.model_dump()
    for name, value in extracted.model_dump(exclude_none=True).items():
        values[name] = value
        # A newly named record replaces the earlier resolution.
        if name in ("task", "project", "parent"):
            values[f"{name}_id"] = None
            if name == "task":
                values["task_label"] = None
    return Pending(intent=intent, slots=Slots(**values), round=min(pending.round + 1, MAX_CLARIFICATION_ROUNDS))


def apply_choice(pending: Pending, choice: Choice) -> Pending:
    values = pending.slots.model_dump()
    values[choice.slot] = choice.value
    if choice.slot == "task_id" and pending.intent != "create_task":
        # The chosen task is exact; a project named earlier only located it.
        values["project"] = values["project_id"] = None
    return Pending(intent=pending.intent, slots=Slots(**values), round=pending.round)


# Which router details each intent may use. Anything else is ignored, so a
# value the model attached to the wrong action can never reach a tool.
ALLOWED = {
    "create_task": ("title", "project", "parent", "deadline", "estimate_minutes", "notes"),
    # On existing-task actions a project only locates the task; it never moves it.
    "update_task": ("task", "project", "title", "notes", "deadline", "estimate_minutes"),
    "assign_task_date": ("task", "project", "date"),
    "complete_task": ("task", "project", "complete"),
    "start_timer": ("task", "project", "duration_minutes"),
    # A task named with a countdown control only checks it is the countdown's task.
    "pause_timer": ("task",),
    "resume_timer": ("task",),
    "finish_timer": ("task",),
    "carry_over_week": ("date",),
    "question": ("task", "project", "date"),
}
TIMER_CONTROLS = ("pause_timer", "resume_timer", "finish_timer")
_RESUME_COMMAND = re.compile(r"^(?:please\s+)?(?:resume|unpause|un-pause)\b")
_REOPEN = re.compile(r"\b(re-?open|undo|unmark|uncheck|incomplete|unfinished|uncomplete|not\s+(yet\s+)?(done|complete|completed|finished))\b")
_COMPLETION_COMMAND = re.compile(r"^(?:please\s+)?mark\s+(?:as\s+)?(?:complete[d]?|done|finished)\b")
_NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "half": 0.5}


def _normal(text: str) -> str:
    # Keep decimal points ("1.5 hours"); drop other punctuation.
    return " ".join(re.sub(r"[\"'“”‘’,!?;:()]|(?<!\d)\.|\.(?!\d)", " ", text.casefold()).split())


def correct_intent(intent: str, message: str) -> str:
    """Code check on the router: "Resume Test #1" resumes, never starts a new countdown.

    Measured Nov 11 (G-06 user testing): the router filed "Resume the test #1" as
    start_timer, which then asked for minutes.
    """
    if intent in ("start_timer", "unsupported") and _RESUME_COMMAND.search(_normal(message)):
        return "resume_timer"
    return intent


def ground(intent: str, extracted: Slots, message: str) -> tuple[Slots, list[str]]:
    """Keep only details the action uses and the user's message actually states.

    The router is a small local model; it can attach invented values (for example
    an estimate nobody mentioned). Text must appear in the message, numbers must
    appear as digits or as hours, and reopening needs an explicit reopen phrase.
    Returns the grounded details and the names of ignored ones.
    """
    said = _normal(message)
    words = said.split()
    kept: dict[str, Any] = {}
    ignored: list[str] = []
    for name, value in extracted.model_dump(exclude_none=True).items():
        if intent == "update_task" and _COMPLETION_COMMAND.search(said) and name in ("notes", "title", "deadline", "estimate_minutes"):
            # A contradictory model route must ask again, never reinterpret a
            # clear completion command as a field edit (e.g. a title with Notes).
            ignored.append(name)
            continue
        if name not in ALLOWED[intent]:
            ignored.append(name)
            continue
        if isinstance(value, bool):
            grounded = value or bool(_REOPEN.search(said))
        elif isinstance(value, int):
            hours = [_NUMBER_WORDS.get(word) or (float(word) if re.fullmatch(r"\d+(\.\d+)?", word) else None)
                     for index, word in enumerate(words) if index + 1 < len(words) and words[index + 1].startswith("hour")]
            grounded = str(value) in words or any(h is not None and h * 60 == value for h in hours)
        else:
            grounded = bool(_normal(value)) and f" {_normal(value)} " in f" {said} "
        if grounded:
            kept[name] = value
        else:
            ignored.append(name)
    return Slots(**kept), ignored


def _label(task: Task, tasks: dict[str, Task], projects: dict[str, str]) -> str:
    parent = tasks.get(task.parent_id or "")
    where = projects.get(task.project_id, "") + (f" / {parent.title}" if parent else "")
    state = "complete" if task.completed else "incomplete"
    return f"{task.title} — {where} ({state})" if where else f"{task.title} ({state})"


def _matches(items: list[Any], text: str, name) -> list[Any]:
    """Exact case-insensitive name first; otherwise contained words. Never fuzzy."""
    needle = text.strip().casefold()
    exact = [item for item in items if name(item).casefold() == needle]
    return exact or [item for item in items if needle and needle in name(item).casefold()]


@dataclass
class Gate:
    """Outcome of the sufficiency check: a proposal, questions, or a blocked request."""
    pending: Pending
    proposal: dict | None = None
    questions: list[str] | None = None
    choices: dict[str, list[dict[str, str]]] | None = None
    blocked: str | None = None


_WEEKDAYS = {name: index for index, names in enumerate((
    ("monday", "mon"), ("tuesday", "tue", "tues"), ("wednesday", "wed"), ("thursday", "thu", "thur", "thurs"),
    ("friday", "fri"), ("saturday", "sat"), ("sunday", "sun"))) for name in names}
_MONTHS = {name: index + 1 for index, names in enumerate((
    ("january", "jan"), ("february", "feb"), ("march", "mar"), ("april", "apr"), ("may",), ("june", "jun"),
    ("july", "jul"), ("august", "aug"), ("september", "sep", "sept"), ("october", "oct"), ("november", "nov"),
    ("december", "dec"))) for name in names}


def parse_day(text: str, today: date) -> date | None:
    """Turn the user's day words into a date without a model; None means ask.

    Accepted: YYYY-MM-DD; today/tomorrow; a weekday or "this <weekday>" (next
    occurrence, today included); "next <weekday>" (that day in the following
    Monday–Sunday week); "<month> <day>[, year]" or "<day> <month> [year]"
    (without a year, the next occurrence). Numeric forms like 11/12 are ambiguous.
    """
    words = re.sub(r"[,.]|\b(on|the|of|by|due)\b|(?<=\d)(st|nd|rd|th)\b", " ", text.strip().casefold()).split()
    phrase = " ".join(words)
    if _DATE.fullmatch(phrase):
        try:
            return date.fromisoformat(phrase)
        except ValueError:
            return None
    if phrase in ("today", "tomorrow"):
        return today + timedelta(days=phrase == "tomorrow")
    if len(words) in (1, 2) and words[-1] in _WEEKDAYS and (len(words) == 1 or words[0] in ("this", "next")):
        target = _WEEKDAYS[words[-1]]
        if words[0] == "next":
            following_monday = today + timedelta(days=7 - today.weekday())
            return following_monday + timedelta(days=target)
        return today + timedelta(days=(target - today.weekday()) % 7)
    month = day = year = None
    for word in words:
        if word in _MONTHS and month is None:
            month = _MONTHS[word]
        elif word.isdigit() and len(word) <= 2 and day is None:
            day = int(word)
        elif word.isdigit() and len(word) == 4 and year is None:
            year = int(word)
        else:
            return None
    if month is None or day is None:
        return None
    try:
        found = date(year or today.year, month, day)
        if year is None and found < today:
            found = date(today.year + 1, month, day)
    except ValueError:
        return None
    return found


_CALLED = re.compile(r"\b(?:called|named|titled)\s+[\"“']?(.+?)[\"”']?(?=\s+(?:under|in|into|due|for|with|to|and)\b|[.?!,;]|$)", re.IGNORECASE)
_UNDER = re.compile(r"\bunder\s+(?:the\s+)?(?:task\s+)?[\"“']?(.+?)[\"”']?(?=\s+(?:in|due|for|with)\b|[.?!,;]|$)", re.IGNORECASE)


def _fill_creation(values: dict[str, Any], message: str, project_names: list[str]) -> None:
    """Fill creation details the router omitted, only from the user's exact words.

    Measured: qwen3:8b sometimes drops "in Biology" or files the new title as an
    existing task. A title after called/named/titled, a parent after "under",
    and one exact project name outside the title are all stated text, so using
    them is not a guess; router values that passed grounding take precedence.
    """
    if not values["title"]:
        found = _CALLED.search(message)
        values["title"] = found.group(1).strip() if found else None
    if not values["parent"] and not values["parent_id"]:
        found = _UNDER.search(message)
        if found:
            destination = found.group(1).strip()
            # "under this History project" names a project, not a task.
            # An explicit "task" marker still permits titles containing "project".
            explicit_task = re.search(r"\bunder\s+(?:the\s+)?task\s+", message, re.IGNORECASE)
            project = re.fullmatch(r"(?:(?:this|the)\s+)?project\s+[\"“']?(.+?)[\"”']?", destination, re.IGNORECASE)
            project = project or re.fullmatch(r"(?:(?:this|the)\s+)?(.+?)\s+project", destination, re.IGNORECASE)
            if project and not explicit_task:
                if not values["project"] and not values["project_id"]:
                    values["project"] = project.group(1).strip(' \"“”\'')
            else:
                values["parent"] = destination
    if not values["project"] and not values["project_id"] and not values["parent"]:
        rest = _normal(message)
        for text in (values["title"], values["parent"]):
            if text:
                rest = rest.replace(_normal(text), " ")
        named = [name for name in project_names if re.search(rf"\b{re.escape(_normal(name))}\b", rest)]
        values["project"] = named[0] if len(named) == 1 else None


_IN_PROJECT = re.compile(
    r"\bin\s+(?:the\s+)?(?:project\s+[\"“']?(?P<after>[^\"”'.?!,;\s]+)|[\"“']?(?P<before>[^\"”'.?!,;]+?)[\"”']?\s+project\b)",
    re.IGNORECASE)


def _fill_locating_project(values: dict[str, Any], message: str, project_names: list[str]) -> None:
    """The project the user named for an existing task, when the router omitted it.

    "Test #1 in Projecting project" must never act on Test #1 in Testing, so an
    explicit "in <name> project" or "in project <name>" is used even when no such
    project exists (the gate then says so). Otherwise one exact project name
    outside the task's words is used. Both are the user's own stated text.
    """
    if values["project"] or values["project_id"] or not message:
        return
    rest = message
    if values["task"]:
        rest = re.sub(re.escape(values["task"]), " ", rest, flags=re.IGNORECASE)
    found = _IN_PROJECT.search(rest)
    if found:
        values["project"] = (found.group("after") or found.group("before")).strip()
        return
    said = _normal(rest)
    named = [name for name in project_names if re.search(rf"\b{re.escape(_normal(name))}\b", said)]
    values["project"] = named[0] if len(named) == 1 else None


def evaluate(db: Database, timer: TimerService | None, pending: Pending, today: date | None = None,
             message: str = "") -> Gate:
    """Resolve records and check every required detail; never guess a missing one."""
    spec = LIBRARY[pending.intent]
    values = pending.slots.model_dump()
    questions: list[str] = []
    choices: dict[str, list[dict[str, str]]] = {}
    tasks = list_tasks(db)
    by_id = {task.id: task for task in tasks}
    projects = {project.id: project.name for project in list_projects(db)}
    if pending.intent == "create_task" and message:
        _fill_creation(values, message, list(projects.values()))
    elif "task" in spec.required:
        _fill_locating_project(values, message, list(projects.values()))

    def resolve_project(missing: str) -> bool:
        """Resolve a named project to its ID. False means a question was asked."""
        if values["project_id"] is not None and values["project_id"] not in projects:
            values["project_id"] = None
        if values["project_id"] is not None or not values["project"]:
            return True
        found = _matches(list(projects.items()), values["project"], lambda item: item[1])
        if len(found) == 1:
            values["project_id"] = found[0][0]
            return True
        if not found:
            questions.append(f"I couldn't find a project named “{values['project']}”. {missing}")
            values["project"] = None
        else:
            questions.append(f"Several projects match “{values['project']}”. Which one?")
            choices["project_id"] = [{"value": key, "label": name} for key, name in found[:MAX_CHOICES]]
        return False

    def offer_elsewhere(text: str, where: str) -> None:
        """The task exists, but not where the user said: say where, never act on it."""
        found = _matches(tasks, text, lambda task: task.title)
        if not found:
            return
        places = sorted({projects.get(task.project_id, "") for task in found} - {""})
        if len(found) == 1 and places:
            questions.append(f"“{found[0].title}” is in {places[0]}, not {where}. Choose it below if you meant that task.")
        else:
            questions.append(f"Tasks matching “{text}” are in other projects. Choose one below if you meant it.")
        choices["task_id"] = [{"value": task.id, "label": _label(task, by_id, projects)} for task in found[:MAX_CHOICES]]

    def resolve_task(slot: str, text_slot: str, pool: list[Task], prompt: str) -> None:
        if values[slot] is not None:
            if values[slot] not in by_id or by_id[values[slot]] not in pool:
                values[slot] = None
            else:
                if slot == "task_id":
                    values["task_label"] = _label(by_id[values[slot]], by_id, projects)
                return
        text = values[text_slot]
        if not text:
            if text_slot in spec.required:
                questions.append(QUESTIONS[text_slot])
            return
        found = _matches(pool, text, lambda task: task.title)
        if len(found) > 1 and message:
            # "Reading in History": a project the user named narrows duplicates.
            said = f" {_normal(message)} "
            named = [task for task in found if f" {_normal(projects.get(task.project_id, ''))} " in said]
            if named and len({task.project_id for task in named}) == 1:
                found = named
        if len(found) == 1:
            values[slot] = found[0].id
            if slot == "task_id":
                values["task_label"] = _label(found[0], by_id, projects)
        elif not found:
            in_project = slot == "task_id" and pending.intent != "create_task" and values["project_id"]
            if in_project and _matches(tasks, text, lambda task: task.title):
                offer_elsewhere(text, projects[values["project_id"]])
            else:
                questions.append(f"I couldn't find a task matching “{text}”. {prompt}")
                values[text_slot] = None
        else:
            questions.append(f"Several tasks match “{text}”. Which one do you mean?")
            choices[slot] = [{"value": task.id, "label": _label(task, by_id, projects)} for task in found[:MAX_CHOICES]]
            if len(found) > MAX_CHOICES:
                questions.append(f"Showing {MAX_CHOICES} of {len(found)} matches; give a more exact title if yours is missing.")

    if "task" in spec.required:
        named_project = values["project"]
        if resolve_project("Which project is the task in?"):
            pool = [task for task in tasks if task.project_id == values["project_id"]] if values["project_id"] else tasks
            resolve_task("task_id", "task", pool, "What is its exact title?")
        elif values["task"] and not values["task_id"]:
            offer_elsewhere(values["task"], f"“{named_project}”")
    if pending.intent == "create_task":
        if values["parent"] or values["parent_id"]:
            resolve_task("parent_id", "parent", [task for task in tasks if task.parent_id is None],
                         "Which existing top-level task should it go under?")
        resolve_project("Which project, or leave it in the default project?")
        if not values["title"]:
            questions.append(QUESTIONS["title"])
    if today is None:
        from backend.domain.calendar import application_today
        today = application_today()[0]
    for slot in ("date", "deadline"):
        if values[slot] is not None:
            day = parse_day(values[slot], today)
            if day is None:
                questions.append(f"I couldn't tell which {slot} “{values[slot]}” means. Give a date like “November 12” or 2026-11-12.")
            values[slot] = day.isoformat() if day else None
    if "date" in spec.required and values["date"] is None and not any("date" in q for q in questions):
        questions.append(QUESTIONS["date"])
    if pending.intent == "start_timer":
        duration = values["duration_minutes"]
        if duration is None or not 1 <= duration <= 180:
            values["duration_minutes"] = None
            questions.append(QUESTIONS["duration_minutes"])
    if pending.intent == "update_task" and not any(values[name] is not None for name in ("title", "notes", "deadline", "estimate_minutes")):
        if not any("date" in q for q in questions):
            questions.append(QUESTIONS["change"])

    resolved = Pending(intent=pending.intent, slots=Slots(**values), round=pending.round)
    if pending.intent in TIMER_CONTROLS and values["task"] and timer is not None:
        active = timer.get().active_session
        named = re.sub(r"^(?:the|my)\s+", "", values["task"].strip(), flags=re.IGNORECASE)
        if active is not None and not _matches([active.task_title], named, lambda title: title):
            return Gate(resolved, blocked=f"The current countdown is for “{active.task_title}”, not “{values['task']}”. "
                                          "Nothing was changed.")
    if questions:
        return Gate(resolved, questions=questions, choices=choices or None)
    if pending.intent == "complete_task" and not by_id[values["task_id"]].subtask_count:
        wanted = values["complete"] is not False
        if by_id[values["task_id"]].completed == wanted:
            return Gate(resolved, blocked=f"“{by_id[values['task_id']].title}” is already {'complete' if wanted else 'incomplete'}. Nothing needs to change.")
    if pending.intent == "carry_over_week":
        day = date.fromisoformat(values["date"]) if values["date"] else (
            today - timedelta(days=7) if re.search(r"\b(last|previous) week\b", message, re.IGNORECASE) else today)
        values = {**values, "week_start": (day - timedelta(days=day.weekday())).isoformat()}
    try:
        proposal = propose_action(db, timer, spec.tool, _arguments(pending.intent, values))
    except InvalidInput as exc:
        return Gate(resolved, blocked=exc.message)
    return Gate(resolved, proposal=proposal)


def _arguments(intent: str, values: dict[str, Any]) -> dict[str, Any]:
    """Map sufficient details onto the tool's fixed schema."""
    if intent == "create_task":
        names = ("title", "project_id", "parent_id", "notes", "deadline", "estimate_minutes")
        return {name: values[name] for name in names if values[name] is not None}
    if intent == "update_task":
        return {"task_id": values["task_id"], **{name: values[name] for name in ("title", "notes", "deadline", "estimate_minutes")
                                                 if values[name] is not None}}
    if intent == "assign_task_date":
        return {"task_id": values["task_id"], "date": values["date"]}
    if intent == "complete_task":
        return {"task_id": values["task_id"], "complete": values["complete"] is not False}
    if intent == "start_timer":
        return {"task_id": values["task_id"], "duration_minutes": values["duration_minutes"]}
    if intent == "carry_over_week":
        return {"week_start": values["week_start"]}
    return {}
