import { useEffect, useId, useState } from "react";
import { ApiError, setTaskCompletion, type Planning, type Project, type Task } from "./api";
import { StartTrackingButton } from "./Countdown";
import { DailyStreak } from "./DailyStreak";

const dateLabel = new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric", timeZone: "UTC" });

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
};

function TodayRow({ task, context, onRun, onTrack, onSaved, locked }: { task: Task; context: string; onRun: Props["onRun"]; onTrack: Props["onTrack"]; onSaved: (id: string, complete: boolean) => void; locked: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return <li className={`today-task${task.completed ? " today-task-complete" : ""}`}>
    <input id={`today-task-${task.id}`} type="checkbox" checked={task.completed} disabled={busy || locked} aria-label={`${task.title} — ${context}`} onChange={async (event) => {
      const complete = event.currentTarget.checked;
      setBusy(true); setError("");
      try { await onRun(() => setTaskCompletion(task.id, complete), complete ? "Task marked complete." : "Task reopened."); onSaved(task.id, complete); }
      catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not save this task. Try again."); }
      finally { setBusy(false); }
    }} />
    <div className="today-task-content"><span className="today-task-title">{task.title}</span>{!task.completed ? <span className="today-task-context">{context}</span> : null}
      {error ? <p role="alert" className="error">{error}</p> : null}</div>
    {!task.completed ? <StartTrackingButton task={task} onTrack={() => onTrack(task.id)} disabled={busy || locked} label="Start" accessibleLabel={`Start ${task.title}`} /> : null}
  </li>;
}

/** A projection of existing active placements, never a copy of task state. */
export function Today({ plan, projects, loading, error, onRun, onTrack, locked, visible, lastSessionId, onRetry }: Props) {
  const [showCompleted, setShowCompleted] = useState(false);
  const [pendingFocus, setPendingFocus] = useState<{ id: string; complete: boolean } | null>(null);
  const disclosureId = useId();
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
  const rows = (plan?.placements ?? []).filter((placement) => placement.planned_date === plan?.today)
    .map((placement) => tasks.get(placement.task_id)).filter((task): task is Task => Boolean(task && task.subtask_count === 0));
  const incomplete = rows.filter((task) => !task.completed);
  const completed = rows.filter((task) => task.completed);
  const row = (task: Task) => {
    const context = [names.get(task.project_id) ?? "Project", task.parent_id ? tasks.get(task.parent_id)?.title : null].filter(Boolean).join(" / ");
    return <TodayRow key={task.id} task={task} context={context} onRun={onRun} onTrack={onTrack} locked={locked} onSaved={(id, complete) => setPendingFocus({ id, complete })} />;
  };
  return <section className="today-view" aria-labelledby="today-heading">
    <div className="today-heading"><h2 id="today-heading">Today</h2>{plan ? <time dateTime={plan.today}>{dateLabel.format(new Date(`${plan.today}T00:00:00Z`))}</time> : null}</div>
    <DailyStreak visible={visible} lastSessionId={lastSessionId} compact />
    {loading && !plan ? <p role="status">Loading today's tasks…</p> : null}
    {error ? <p className="error">Today's tasks may be out of date. <button type="button" className="link" onClick={onRetry}>Retry</button></p> : null}
    {plan ? <>
      <p className="today-count">{incomplete.length} unfinished · {completed.length} complete</p>
      {incomplete.length ? <ul className="today-tasks">{incomplete.map(row)}</ul> : <p className="today-empty">No unfinished tasks planned for today.</p>}
      {completed.length ? <div className="today-completed"><button id={disclosureId} type="button" className="link" aria-expanded={showCompleted} onClick={() => setShowCompleted((value) => !value)}>Completed · {completed.length}</button>{showCompleted ? <ul className="today-tasks">{completed.map(row)}</ul> : null}</div> : null}
    </> : null}
  </section>;
}
