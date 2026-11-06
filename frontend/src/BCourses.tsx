import { createPortal } from "react-dom";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  ApiError, addBCoursesAssignment, dismissBCoursesAssignment, followBCourses, getBCourses, refreshBCourses,
  resolveBCoursesDueDate, type BCoursesAssignment, type BCoursesState,
} from "./api";

const dueLabel = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
const dayLabel = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });
const stampLabel = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

const day = (iso: string) => dayLabel.format(new Date(`${iso}T00:00:00Z`));
const message = (caught: unknown, fallback: string) => caught instanceof ApiError ? caught.message : fallback;

function Item({ item, children }: { item: BCoursesAssignment; children?: React.ReactNode }) {
  return <li className="bcourses-item">
    <div className="bcourses-item-text">
      <strong>{item.title}</strong>
      <span className="muted">{item.course_name}</span>
      <span>{item.due_at ? `Due ${dueLabel.format(new Date(item.due_at))}` : "No due date"}
        {item.points_possible != null ? ` · ${item.points_possible} pts` : ""}
        {!item.in_source ? " · No longer listed in bCourses" : ""}</span>
      {item.html_url ? <a href={item.html_url} target="_blank" rel="noreferrer noopener">Open in bCourses</a> : null}
    </div>
    {children ? <div className="bcourses-item-actions">{children}</div> : null}
  </li>;
}

export function BCourses({ visible, settingsVisible, coursePanel, onChanged, onOpenSettings }: {
  visible: boolean;
  settingsVisible?: boolean;
  coursePanel?: HTMLElement | null;
  onChanged?: () => void;
  onOpenSettings?: React.MouseEventHandler<HTMLAnchorElement>;
}) {
  const [state, setState] = useState<BCoursesState | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [draft, setDraft] = useState<Set<string> | null>(null);
  const reviewHeading = useRef<HTMLHeadingElement>(null);
  const loaded = useRef(false);
  const actionRunning = useRef(false);
  const [loadAttempt, setLoadAttempt] = useState(0);

  async function run(label: string, action: () => Promise<BCoursesState>, done = "", selection?: string[]) {
    if (actionRunning.current) return;
    actionRunning.current = true;
    setBusy(label);
    setError(null);
    setStatus("");
    try {
      setState(await action());
      if (selection) setDraft(null);
      if (done) setStatus(done);
    } catch (caught) {
      const failure = message(caught, "Could not confirm the bCourses action. Refresh to check what was saved.");
      setError(failure);
      try {
        const next = await getBCourses();
        setState(next);
        if (selection) {
          const saved = next.courses.filter((course) => course.followed);
          if (saved.length === selection.length && saved.every((course) => selection.includes(course.course_id))) {
            setDraft(null);
            setError(`Your course selection is saved. Assignments may be out of date. Use Refresh to retry. ${failure}`);
          }
        }
      } catch { /* keep the current view and draft */ }
    } finally {
      actionRunning.current = false;
      setBusy(null);
    }
  }

  useLayoutEffect(() => {
    if (visible) reviewHeading.current?.focus();
  }, [visible]);

  const active = visible || settingsVisible;
  useEffect(() => {
    if (!active || loaded.current) return;
    const controller = new AbortController();
    setBusy("load");
    setError(null);
    void (async () => {
      try {
        const first = await getBCourses(controller.signal);
        if (controller.signal.aborted) return;
        loaded.current = true;
        setState(first);
      } catch (caught) {
        if (!controller.signal.aborted) setError(message(caught, "Could not read bCourses."));
      } finally {
        if (!controller.signal.aborted) setBusy(null);
      }
    })();
    return () => controller.abort();
  }, [active, loadAttempt]);

  const followed = state?.courses.filter((course) => course.followed) ?? [];
  const chosen = draft ?? new Set(followed.map((course) => course.course_id));
  const now = Date.now();
  const items = state?.assignments ?? [];
  const changed = items.filter((item) => item.status === "added" && item.due_changed);
  const fresh = items.filter((item) => item.status === "new");
  const upcoming = fresh.filter((item) => item.due_at && new Date(item.due_at).getTime() >= now);
  const undated = fresh.filter((item) => !item.due_at);
  const past = fresh.filter((item) => item.due_at && new Date(item.due_at).getTime() < now).reverse();
  const added = items.filter((item) => item.status === "added");
  const dismissed = items.filter((item) => item.status === "dismissed");

  const add = (item: BCoursesAssignment) => run(`add:${item.assignment_id}`, async () => {
    const result = await addBCoursesAssignment(item.assignment_id);
    onChanged?.();
    setStatus(`Added “${result.task.title}” to ${item.course_name}${result.task.deadline ? `, due ${day(result.task.deadline)}` : ""}.`);
    return getBCourses();
  });
  const dismiss = (item: BCoursesAssignment, value: boolean) => run(`dismiss:${item.assignment_id}`, async () => {
    await dismissBCoursesAssignment(item.assignment_id, value);
    return getBCourses();
  }, value ? `Dismissed “${item.title}”.` : `Restored “${item.title}”.`);
  const resolve = (item: BCoursesAssignment, useNew: boolean) => run(`due:${item.assignment_id}`, async () => {
    await resolveBCoursesDueDate(item.assignment_id, useNew);
    if (useNew) onChanged?.();
    return getBCourses();
  }, useNew ? `Updated the due date of “${item.title}”.` : `Kept your due date for “${item.title}”.`);

  const actions = (item: BCoursesAssignment) => <>
    <button type="button" disabled={busy !== null} onClick={() => void add(item)} aria-label={`Add “${item.title}” as a task`}>Add</button>
    <button type="button" className="link" disabled={busy !== null} onClick={() => void dismiss(item, true)} aria-label={`Dismiss “${item.title}”`}>Dismiss</button>
  </>;
  const list = (label: string, entries: BCoursesAssignment[]) => <ul className="bcourses-list" aria-label={label}>
    {entries.map((item) => <Item key={item.assignment_id} item={item}>{actions(item)}</Item>)}
  </ul>;

  const refresh = () => void run("refresh", refreshBCourses, "Updated from bCourses.");
  const feedback = <>
    {error ? <p role="alert" className="error">{error}</p> : null}
    {error && !state ? <button type="button" disabled={busy !== null} onClick={() => setLoadAttempt((attempt) => attempt + 1)}>Retry status</button> : null}
    {state?.sync.last_error && !error ? <p role="alert" className="error">Last refresh failed: {state.sync.last_error}</p> : null}
    {status ? <p role="status">{status}</p> : null}
  </>;

  return <>
    {coursePanel ? createPortal(<>
      {state ? <p className="muted">{state.sync.last_success_at ? `Last assignment refresh ${stampLabel.format(new Date(state.sync.last_success_at))}` : "No successful assignment refresh recorded."}</p> : null}
      <details className="bcourses-courses">
        <summary>Manage courses ({followed.length} followed)</summary>
        {feedback}
        {state?.courses.length ? <fieldset disabled={busy !== null || !state.configured}>
          <legend>Choose the courses whose assignments you want to see</legend>
          {state.courses.filter((course) => course.in_source || course.followed).map((course) => <label key={course.course_id}>
            <input type="checkbox" checked={chosen.has(course.course_id)} onChange={(event) => {
              const next = new Set(chosen);
              if (event.target.checked) next.add(course.course_id); else next.delete(course.course_id);
              setDraft(next);
            }} />
            <span>{course.name}{course.term ? <span className="muted"> · {course.term}</span> : null}</span>
          </label>)}
        </fieldset> : <p className="muted">{state?.configured ? "Refresh to load your bCourses course list." : state ? "Save a bCourses token to load courses." : busy === "load" ? "Loading course status…" : "Course status is unavailable."}</p>}
        <div className="form-actions connection-actions">
          <button type="button" className="secondary" disabled={busy !== null || !state?.configured} onClick={refresh}>
            {busy === "refresh" ? "Refreshing…" : "Refresh"}</button>
          {state?.courses.length ? <button type="button" disabled={busy !== null || !state.configured || !draft}
            onClick={() => {
              const selection = [...chosen];
              void run("follow", () => followBCourses(selection), "Saved your courses and updated assignments.", selection);
            }}>{busy === "follow" ? "Saving…" : "Save courses"}</button> : null}
        </div>
        <p className="muted">Assignments become local tasks when you choose Add. Removing a course from this list keeps tasks you already added.</p>
      </details>
    </>, coursePanel) : null}
    <section hidden={!visible} className="bcourses" aria-label="bCourses" aria-busy={busy !== null}>
      <div className="forest-heading"><h2 ref={reviewHeading} tabIndex={-1}>bCourses</h2>
        <button type="button" disabled={busy !== null || !state?.configured} onClick={refresh}>
          {busy === "refresh" ? "Refreshing…" : "Refresh"}</button>
      </div>
      <p className="muted">Assignments from the courses you follow wait here. Nothing becomes a task until you choose Add. BearPlans only reads bCourses; it never changes anything there.</p>
      {state?.sync.last_success_at ? <p className="muted">Last updated {stampLabel.format(new Date(state.sync.last_success_at))}.</p> : null}
      {feedback}
      <a href="#settings" onClick={onOpenSettings}>Manage courses in Settings</a>
      {state && !state.configured ? <p className="bcourses-setup">No bCourses token is set. <a href="#settings" onClick={onOpenSettings}>Open Settings</a> to add one.</p> : null}

      {changed.length ? <>
        <h3>Due date changed in bCourses</h3>
        <ul className="bcourses-list" aria-label="Due date changed">
          {changed.map((item) => <Item key={item.assignment_id} item={item}>
            <span>Your task: {item.accepted_due_date ? day(item.accepted_due_date) : "no due date"} → bCourses: {item.due_date ? day(item.due_date) : "no due date"}</span>
            <button type="button" disabled={busy !== null} onClick={() => void resolve(item, true)}>Use new due date</button>
            <button type="button" className="link" disabled={busy !== null} onClick={() => void resolve(item, false)}>Keep mine</button>
          </Item>)}
        </ul>
      </> : null}

      {followed.length ? <>
        <h3>Upcoming ({upcoming.length})</h3>
        {upcoming.length ? list("Upcoming assignments", upcoming) : <p className="muted">No new upcoming assignments.</p>}
        <h3>No due date ({undated.length})</h3>
        {undated.length ? list("Assignments with no due date", undated) : <p className="muted">None.</p>}
        {past.length ? <details><summary>Past due, not added ({past.length})</summary>{list("Past due assignments", past)}</details> : null}
        {added.length ? <details><summary>Added as tasks ({added.length})</summary>
          <ul className="bcourses-list" aria-label="Added assignments">{added.map((item) => <Item key={item.assignment_id} item={item} />)}</ul></details> : null}
        {dismissed.length ? <details><summary>Dismissed ({dismissed.length})</summary>
          <ul className="bcourses-list" aria-label="Dismissed assignments">{dismissed.map((item) => <Item key={item.assignment_id} item={item}>
            <button type="button" className="link" disabled={busy !== null} onClick={() => void dismiss(item, false)}>Restore</button>
          </Item>)}</ul></details> : null}
      </> : state?.configured ? <p className="muted">Choose courses in Settings to see their assignments here.</p> : null}
    </section>
  </>;
}
