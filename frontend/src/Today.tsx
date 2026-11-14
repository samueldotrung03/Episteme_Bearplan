import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ApiError, assignTask, setTaskCompletion, type EarlierUnfinishedTask, type GoogleEvent, type Planning, type Project, type Task } from "./api";
import { DailyStreak } from "./DailyStreak";

const dateLabel = new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric", timeZone: "UTC" });
const weekdayLabel = new Intl.DateTimeFormat(undefined, { weekday: "long", timeZone: "UTC" });
const monthDayLabel = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", timeZone: "UTC" });
const eventClock = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

type Props = {
  plan: Planning | null;
  projects: Project[];
  loading: boolean;
  error: string | null;
  locked: boolean;
  visible: boolean;
  lastSessionId: string | null;
  onRun: (work: () => Promise<unknown>, done: string) => Promise<void>;
  onTrack: (taskId: string) => void;
  onRetry: () => void;
  /** Plan view controls (Today/Week, Projects, Add task) shown beside the title. */
  headerActions?: ReactNode;
  /** Keyboard shortcuts N, W and P. Omitted handlers leave the key unused. */
  onAddTask?: () => void;
  onShowWeek?: () => void;
  onShowProjects?: () => void;
};

export function formatPlanned(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return hours ? `${hours}h${rest ? ` ${rest}m` : ""}` : `${rest}m`;
}

function eventTime(event: GoogleEvent): string {
  if (event.all_day || !event.start_at) return "All day";
  return `${eventClock.format(new Date(event.start_at))} – ${eventClock.format(new Date(event.end_at ?? event.start_at))}`;
}

type RowProps = {
  task: Task;
  context: string;
  startTime: string | null;
  focused: boolean;
  locked: boolean;
  onFocusRow: () => void;
  onRun: Props["onRun"];
  onTrack: Props["onTrack"];
  onSaved: (id: string, complete: boolean) => void;
};

function TodayRow({ task, context, startTime, focused, locked, onFocusRow, onRun, onTrack, onSaved }: RowProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const complete = async (value: boolean) => {
    setBusy(true); setError("");
    try { await onRun(() => setTaskCompletion(task.id, value), value ? "Task marked complete." : "Task reopened."); onSaved(task.id, value); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not save this task. Try again."); }
    finally { setBusy(false); }
  };
  const className = ["today-task", task.completed ? "today-task-complete" : "", focused ? "today-task-focused" : ""].filter(Boolean).join(" ");
  return <li className={className} data-task-id={task.id} onFocus={onFocusRow}>
    <span className="today-check">
      <input id={`today-task-${task.id}`} type="checkbox" checked={task.completed} disabled={busy || locked} aria-label={`${task.title} — ${context}`}
        onChange={(event) => void complete(event.currentTarget.checked)} />
    </span>
    <div className="today-task-content">
      <span className="today-task-title">{task.title}</span>
      {!task.completed ? <span className="today-task-context">{context}</span> : null}
      {error ? <p role="alert" className="error">{error}</p> : null}
    </div>
    {!task.completed ? <div className="today-task-trailing">
      {startTime ? <span className="today-task-start">{startTime}</span> : null}
      {task.estimate_minutes ? <span className="today-task-estimate">{task.estimate_minutes} min</span> : null}
      <button type="button" className={`today-start${focused ? " primary" : ""}`} aria-label={`Start ${task.title}`} disabled={busy || locked} onClick={() => onTrack(task.id)}>
        <span className="icon icon-play" aria-hidden="true" />Start
      </button>
    </div> : null}
  </li>;
}

/** "from Thursday" within the last six days, otherwise "from Nov 3". */
export function earlierFrom(date: string, today: string): string {
  const days = (Date.parse(`${today}T00:00:00Z`) - Date.parse(`${date}T00:00:00Z`)) / 86_400_000;
  const when = new Date(`${date}T00:00:00Z`);
  return `from ${days >= 1 && days <= 6 ? weekdayLabel.format(when) : monthDayLabel.format(when)}`;
}

function EarlierRow({ task, today, locked, onRun }: { task: EarlierUnfinishedTask; today: string; locked: boolean; onRun: Props["onRun"] }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const context = [task.project_name, task.parent_title, earlierFrom(task.last_planned_date, today)].filter(Boolean).join(" · ");
  return <li className="today-task" data-task-id={task.id}>
    <span className="today-check">
      <input type="checkbox" checked={false} disabled={busy || locked} aria-label={`${task.title} — ${context}`} onChange={async () => {
        setBusy(true); setError("");
        try { await onRun(() => setTaskCompletion(task.id, true), "Task marked complete."); }
        catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not save this task. Try again."); }
        finally { setBusy(false); }
      }} />
    </span>
    <div className="today-task-content">
      <span className="today-task-title">{task.title}</span>
      <span className="today-task-context">{context}</span>
      {error ? <p role="alert" className="error">{error}</p> : null}
    </div>
    {task.estimate_minutes ? <div className="today-task-trailing"><span className="today-task-estimate">{task.estimate_minutes} min</span></div> : null}
  </li>;
}

function EarlierUnfinished({ items, today, locked, onRun }: { items: EarlierUnfinishedTask[]; today: string; locked: boolean; onRun: Props["onRun"] }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const listId = useId();
  if (!items.length) return null;
  const label = items.length === 1 ? "Move to today" : items.length === 2 ? "Move both to today" : `Move all ${items.length} to today`;
  // Adds a placement for today to each task; earlier placements stay as history.
  const moveAll = async () => {
    setBusy(true); setError("");
    try {
      await onRun(async () => { for (const task of items) await assignTask(task.id, today); },
        items.length === 1 ? `Planned “${items[0].title}” for today.` : `Planned ${items.length} earlier tasks for today.`);
    } catch (caught) {
      setError(`${caught instanceof ApiError ? caught.message : "Could not plan these tasks."} Any that were planned now show in today's list.`);
    } finally { setBusy(false); }
  };
  return <div className="today-earlier">
    <button type="button" className="disclosure" aria-expanded={open} aria-controls={listId} onClick={() => setOpen((value) => !value)}>
      <span className="icon icon-chevron" aria-hidden="true" />Earlier unfinished · {items.length}
    </button>
    {open ? <div id={listId}>
      <ul className="today-tasks" aria-label="Earlier unfinished tasks">{items.map((task) => <EarlierRow key={task.id} task={task} today={today} locked={locked} onRun={onRun} />)}</ul>
      <div className="today-earlier-actions">
        <button type="button" className="button-tertiary" disabled={busy || locked} onClick={() => void moveAll()}>
          <span className="icon icon-arrow-up" aria-hidden="true" />{busy ? "Planning…" : label}
        </button>
      </div>
      {error ? <p role="alert" className="error">{error}</p> : null}
    </div> : null}
  </div>;
}

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT", "BUTTON", "A"].includes(target.tagName);
}

/** A projection of existing active placements, never a copy of task state. */
export function Today({ plan, projects, loading, error, onRun, onTrack, locked, visible, lastSessionId, onRetry, headerActions, onAddTask, onShowWeek, onShowProjects }: Props) {
  const [showCompleted, setShowCompleted] = useState(false);
  const [pendingFocus, setPendingFocus] = useState<{ id: string; complete: boolean } | null>(null);
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const disclosureId = useId();
  const listRef = useRef<HTMLUListElement>(null);
  useEffect(() => {
    if (!pendingFocus || !plan) return;
    const task = plan.tasks.find((item) => item.id === pendingFocus.id);
    if (!task || task.completed !== pendingFocus.complete) return;
    const target = document.getElementById(pendingFocus.complete ? disclosureId : `today-task-${task.id}`);
    if (target instanceof HTMLInputElement && target.disabled) return;
    if (target) { target.focus(); setPendingFocus(null); }
  }, [plan, pendingFocus, disclosureId, locked]);

  const tasks = new Map((plan?.tasks ?? []).map((task) => [task.id, task]));
  const names = new Map(projects.map((project) => [project.id, project.name]));
  const todays = (plan?.placements ?? []).filter((placement) => placement.planned_date === plan?.today);
  const startTimes = new Map(todays.map((placement) => [placement.task_id, placement.start_time ?? null]));
  const rows = todays.map((placement) => tasks.get(placement.task_id)).filter((task): task is Task => Boolean(task && task.subtask_count === 0));
  const incomplete = rows.filter((task) => !task.completed);
  const completed = rows.filter((task) => task.completed);
  const plannedMinutes = incomplete.reduce((sum, task) => sum + (task.estimate_minutes ?? 0), 0);
  const events = (plan?.calendar_events ?? []).filter((event) => plan && event.first_day <= plan.today && event.last_day >= plan.today);
  const focused = incomplete.find((task) => task.id === focusedId) ?? incomplete[0] ?? null;

  // Shortcuts act only while Today is shown, nothing is being typed or pressed,
  // and no dialog is open. Enter/X act on the focused row.
  const latest = useRef({ focused, incomplete, locked, onTrack, onAddTask, onShowWeek, onShowProjects });
  latest.current = { focused, incomplete, locked, onTrack, onAddTask, onShowWeek, onShowProjects };
  useEffect(() => {
    if (!visible) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || isTyping(event.target)) return;
      if (document.querySelector("dialog[open]")) return;
      const current = latest.current;
      const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
      const move = (step: number) => {
        if (!current.incomplete.length) return;
        const index = current.focused ? current.incomplete.indexOf(current.focused) : -1;
        const next = current.incomplete[Math.min(current.incomplete.length - 1, Math.max(0, index + step))];
        setFocusedId(next.id);
        listRef.current?.querySelector<HTMLElement>(`[data-task-id="${next.id}"]`)?.scrollIntoView?.({ block: "nearest" });
      };
      if (key === "ArrowDown" || key === "j") move(1);
      else if (key === "ArrowUp" || key === "k") move(-1);
      else if (key === "Enter" && current.focused && !current.locked) current.onTrack(current.focused.id);
      else if (key === "x" && current.focused && !current.locked) document.getElementById(`today-task-${current.focused.id}`)?.click();
      else if (key === "n" && current.onAddTask) current.onAddTask();
      else if (key === "w" && current.onShowWeek) current.onShowWeek();
      else if (key === "p" && current.onShowProjects) current.onShowProjects();
      else return;
      event.preventDefault();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [visible]);

  const row = (task: Task) => {
    const context = [names.get(task.project_id) ?? "Project", task.parent_id ? tasks.get(task.parent_id)?.title : null].filter(Boolean).join(" / ");
    return <TodayRow key={task.id} task={task} context={context} startTime={startTimes.get(task.id) ?? null} focused={!task.completed && focused?.id === task.id}
      locked={locked} onFocusRow={() => setFocusedId(task.id)} onRun={onRun} onTrack={onTrack} onSaved={(id, complete) => setPendingFocus({ id, complete })} />;
  };

  return <section className="today-view" aria-labelledby="today-heading">
    <div className="plan-header">
      <h2 className="plan-title"><span id="today-heading">Today</span>{plan ? <> <time dateTime={plan.today}>{dateLabel.format(new Date(`${plan.today}T00:00:00Z`))}</time></> : null}</h2>
      {headerActions}
    </div>
    <div className="today-summary">
      <DailyStreak visible={visible} lastSessionId={lastSessionId} compact />
      {plan ? <p className="today-count">{incomplete.length} unfinished · {completed.length} complete{plannedMinutes ? ` · ${formatPlanned(plannedMinutes)} planned` : ""}</p> : null}
    </div>
    {events.length ? <ul className="today-events" aria-label="Calendar events today">
      {events.map((event) => <li key={`${event.calendar_id}/${event.event_id}`} className="today-event">
        <span className="today-event-time">{eventTime(event)}</span>
        <span className="today-event-title">{event.summary}</span>
      </li>)}
    </ul> : null}
    {loading && !plan ? <p role="status">Loading today's tasks…</p> : null}
    {error ? <p className="error">Today's tasks may be out of date. <button type="button" className="link" onClick={onRetry}>Retry</button></p> : null}
    {plan ? <>
      {incomplete.length ? <ul ref={listRef} className="today-tasks">{incomplete.map(row)}</ul> : <p className="today-empty">No unfinished tasks planned for today.</p>}
      {completed.length ? <div className="today-completed">
        <button id={disclosureId} type="button" className="disclosure" aria-expanded={showCompleted} onClick={() => setShowCompleted((value) => !value)}>
          <span className="icon icon-chevron" aria-hidden="true" />Completed · {completed.length}
        </button>
        {showCompleted ? <ul className="today-tasks today-tasks-completed">{completed.map(row)}</ul> : null}
      </div> : null}
      <EarlierUnfinished items={plan.earlier_unfinished ?? []} today={plan.today} locked={locked} onRun={onRun} />
      <p className="today-shortcuts" aria-label="Keyboard shortcuts">
        <span><kbd>Enter</kbd> start focused task</span><span><kbd>X</kbd> complete</span>
        {onAddTask ? <span><kbd>N</kbd> new task</span> : null}{onShowWeek ? <span><kbd>W</kbd> week</span> : null}{onShowProjects ? <span><kbd>P</kbd> projects</span> : null}
        <span><kbd>↑</kbd><kbd>↓</kbd> choose</span>
      </p>
    </> : null}
  </section>;
}
