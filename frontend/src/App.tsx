import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import {
  ApiError,
  ESTIMATE_MAX_MINUTES,
  ESTIMATE_MIN_MINUTES,
  NAME_MAX_LENGTH,
  TITLE_MAX_LENGTH,
  createProject,
  createTask,
  listProjects,
  listTasks,
  renameProject,
  removeSubtask,
  setTaskCompletion,
  updateTask,
  type Project,
  type Task,
  type TaskEdit,
} from "./api";
import { TaskPlanning, WeeklyPlanner, usePlanning } from "./WeeklyPlanner";
import { CompactTimer, StartTrackingButton, TrackScreen, useCountdown } from "./Countdown";
import { Statistics } from "./Statistics";
import { Today } from "./Today";
import navigationTree from "./assets/navigation-tree.svg?no-inline";
import navigationSettings from "./assets/navigation-settings.svg?no-inline";
import { Assistant } from "./Assistant";
import { ConnectionPanels } from "./ConnectionPanels";
import { ConnectionSetup, type SetupProvider } from "./ConnectionSetup";
import { BCourses } from "./BCourses";
import { Google, useGoogleChanges } from "./Google";
import { TaskCaptureForm } from "./TaskCaptureForm";
import { readPendingCapture } from "./taskCaptureRecovery";

const dueOn = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeZone: "UTC" });

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}

/** A deadline is a plain date; parse it as UTC so it never shifts a day in local time. */
function formatDeadline(deadline: string): string {
  return dueOn.format(new Date(`${deadline}T00:00:00Z`));
}

function formatEstimate(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

function readScreen() {
  switch (window.location.hash) {
    case "#assistant": return "assistant";
    case "#track": return "track";
    case "#stats": return "stats";
    case "#bcourses": return "bcourses";
    case "#google": return "google";
    case "#settings": return "settings";
    default: return "plan";
  }
}

export default function App() {
  const planning = usePlanning();
  const timer = useCountdown();
  const [screen, setScreen] = useState(readScreen);
  const [planView, setPlanView] = useState<"today" | "week" | "projects">("today");
  const [setup, setSetup] = useState<{ provider: SetupProvider } | null>(null);
  const [setupNotice, setSetupNotice] = useState("");
  const [credentialVersion, setCredentialVersion] = useState(0);
  const [bcoursesCredentialVersion, setBCoursesCredentialVersion] = useState(0);
  const [coursePanel, setCoursePanel] = useState<HTMLDivElement | null>(null);
  const settingsEntry = useRef<HTMLAnchorElement>(null);
  const settingsHeading = useRef<HTMLHeadingElement>(null);
  const settingsReturn = useRef<{ screen: Exclude<ReturnType<typeof readScreen>, "settings">; scrollY: number } | null>(null);
  const previousScreen = useRef(screen);
  const [trackingTaskId, setTrackingTaskId] = useState<string | null>(null);
  const [trackingRequest, setTrackingRequest] = useState(0);
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [progress, setProgress] = useState<{ completed: number; total: number } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [taskDraftProjects, setTaskDraftProjects] = useState<string[]>([]);
  const addTaskTrigger = useRef<HTMLButtonElement>(null);
  const tasksHeading = useRef<HTMLHeadingElement>(null);
  const [pendingCapture, setPendingCapture] = useState(() => { try { return readPendingCapture(); } catch { return null; } });
  const [reviewPendingCapture, setReviewPendingCapture] = useState(false);
  useEffect(() => {
    const update = () => { try { setPendingCapture(readPendingCapture()); } catch { /* Form reports unavailable recovery storage. */ } };
    window.addEventListener("storage", update); window.addEventListener("bearplans-capture-change", update);
    return () => { window.removeEventListener("storage", update); window.removeEventListener("bearplans-capture-change", update); };
  }, []);
  const [addingSubtaskTo, setAddingSubtaskTo] = useState<string | null>(null);
  const [renaming, setRenaming] = useState(false);
  const [addingProject, setAddingProject] = useState(false);
  const [savingProject, setSavingProject] = useState(false);
  const addProjectTrigger = useRef<HTMLButtonElement>(null);
  const renameProjectTrigger = useRef<HTMLButtonElement>(null);
  const [mutations, setMutations] = useState(0);
  const taskRequest = useRef<AbortController | null>(null);
  // Handlers capture the project that was selected when they were created. A mutation
  // can resolve after the user has moved on, so the refresh needs the current project,
  // not the captured one.
  const selectedIdRef = useRef<string | null>(null);
  selectedIdRef.current = selectedId;

  const selected = projects?.find((p) => p.id === selectedId) ?? null;

  useEffect(() => {
    const navigate = () => {
      const next = readScreen();
      if (next !== "settings") setSetup(null);
      setScreen(next);
    };
    window.addEventListener("hashchange", navigate);
    return () => window.removeEventListener("hashchange", navigate);
  }, []);

  useLayoutEffect(() => {
    if (screen === "settings") {
      settingsReturn.current = window.history.state?.settingsReturn ?? null;
      settingsHeading.current?.focus({ preventScroll: true });
      window.scrollTo(0, 0);
    } else if (previousScreen.current === "settings" && settingsReturn.current?.screen === screen) {
      settingsEntry.current?.focus({ preventScroll: true });
      window.scrollTo(0, settingsReturn.current.scrollY);
    }
    previousScreen.current = screen;
  }, [screen]);

  function openSettings(event: React.MouseEvent<HTMLAnchorElement>) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (screen === "settings") return;
    window.history.pushState({ settingsReturn: { screen, scrollY: window.scrollY } }, "", "#settings");
    setScreen("settings");
  }

  function openAssignmentReview(event: React.MouseEvent<HTMLAnchorElement>) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    settingsReturn.current = null;
    window.history.pushState(null, "", "#bcourses");
    setScreen("bcourses");
  }

  function backToWork() {
    if (settingsReturn.current) {
      window.history.back();
      return;
    }
    window.history.replaceState(null, "", "#plan");
    setScreen("plan");
    settingsEntry.current?.focus({ preventScroll: true });
  }

  function openTrack(taskId?: string) {
    if (taskId) {
      setTrackingTaskId(taskId);
      setTrackingRequest((current) => current + 1);
    }
    setScreen("track");
    window.location.hash = "track";
    timer.refresh();
  }

  const loadProjects = useCallback(() => {
    setLoadError(null);
    return listProjects()
      .then((loaded) => {
        setProjects(loaded);
        setSelectedId((current) => current ?? loaded[0]?.id ?? null);
      })
      .catch((error: unknown) => setLoadError(errorMessage(error)));
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);


  // Completion of a parent is derived from its subtasks, so after any change the
  // service is the only thing that knows the right answer. Always re-read.
  const refreshTasks = useCallback((projectId: string) => {
    taskRequest.current?.abort();
    const controller = new AbortController();
    taskRequest.current = controller;
    return listTasks(projectId, controller.signal)
      .then((loaded) => {
        // Drop a late response for a project the user has already left, or its tasks
        // would appear under another project's heading.
        if (controller.signal.aborted || selectedIdRef.current !== projectId) return true;
        setTasks(loaded.tasks);
        setProgress(loaded.progress);
        setLoadError(null);
        return true;
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setLoadError(errorMessage(error));
        return controller.signal.aborted;
      });
  }, []);

  // Either load can be the one that failed, and selecting the same project again does
  // not re-run the effect, so a retry has to refetch both.
  const retry = useCallback(async () => {
    await loadProjects();
    const current = selectedIdRef.current;
    if (current) await refreshTasks(current);
  }, [loadProjects, refreshTasks]);

  // A background Google sync can tick tasks done or bring new calendar events.
  useGoogleChanges(() => { void retry(); void planning.refresh(); });

  useEffect(() => {
    // Any open form belongs to the project that was selected when it opened, so
    // close them here rather than in one button's handler.
    setEditing(null);
    setAddingSubtaskTo(null);
    setRenaming(false);
    if (!selectedId) return;
    setTasks(null);
    setProgress(null);
    refreshTasks(selectedId);
    return () => taskRequest.current?.abort();
  }, [selectedId, refreshTasks]);

  async function run(work: () => Promise<unknown>, done: string) {
    setMutations((count) => count + 1);
    try {
      await work();
      const current = selectedIdRef.current;
      const refreshed = await Promise.all([current ? refreshTasks(current) : Promise.resolve(true), planning.refresh()]);
      await timer.refresh();
      setStatus(refreshed.every(Boolean) ? done : "Saved. Some views could not refresh. Use the retry controls to see the saved changes.");
    } finally {
      setMutations((count) => count - 1);
    }
  }

  const parents = tasks?.filter((task) => task.parent_id === null) ?? [];
  const subtasksOf = (id: string) => tasks?.filter((task) => task.parent_id === id) ?? [];

  return (
    <main className="page">
      <header className="page-head">
        <div className="app-brand"><img src={navigationTree} alt="" /><h1>BearPlans</h1></div>
        <nav className="main-navigation" aria-label="Main navigation">
          <a href="#plan" aria-current={screen === "plan" ? "page" : undefined} onClick={() => setScreen("plan")}>Plan</a>
          <a href="#track" aria-current={screen === "track" ? "page" : undefined} onClick={() => openTrack()}>Track</a>
          <a href="#stats" aria-current={screen === "stats" ? "page" : undefined} onClick={() => setScreen("stats")}>Stats</a>
          <a href="#assistant" aria-current={screen === "assistant" ? "page" : undefined} onClick={() => setScreen("assistant")}>Assistant</a>
          <a href="#bcourses" aria-current={screen === "bcourses" ? "page" : undefined} onClick={() => setScreen("bcourses")}>bCourses</a>
          <a href="#google" aria-current={screen === "google" ? "page" : undefined} onClick={() => setScreen("google")}>Google</a>
          <a ref={settingsEntry} className="settings-entry" href="#settings" aria-current={screen === "settings" ? "page" : undefined} onClick={openSettings} aria-label="Settings"><img src={navigationSettings} alt="" /></a>
        </nav>
      </header>

      {timer.error ? <p role="alert" className="error timer-error">{timer.error}{" "}<button type="button" className="link" onClick={timer.refresh}>Refresh timer</button></p> : null}
      {screen !== "track" ? <CompactTimer timer={timer} onOpen={() => openTrack()} /> : null}
      <TrackScreen timer={timer} plan={planning.plan} projects={projects ?? []} requestedTaskId={trackingTaskId} requestToken={trackingRequest} visible={screen === "track"} planError={planning.error} onRefreshTasks={() => void planning.refresh()} />
      <Statistics visible={screen === "stats"} />
      <BCourses key={bcoursesCredentialVersion} onOpenSettings={openSettings} visible={screen === "bcourses"}
        settingsVisible={screen === "settings"} coursePanel={coursePanel} onChanged={() => { void retry(); void planning.refresh(); }} />
      <Google onOpenSettings={openSettings} visible={screen === "google"} onChanged={() => { void retry(); void planning.refresh(); }} />
      <Assistant visible={screen === "assistant"} projectId={selectedId} date={planning.plan?.week_start}
        onChanged={() => { if (selectedId) void refreshTasks(selectedId); void planning.refresh(); void timer.refresh(); }} />

      <section className="settings" aria-labelledby="settings-heading" hidden={screen !== "settings"}>
        <div className="settings-heading">
          <h2 id="settings-heading" ref={settingsHeading} tabIndex={-1}>Settings</h2>
          <button type="button" onClick={backToWork}>Back to work</button>
        </div>
        <h3>Connections</h3>
        <ConnectionPanels visible={screen === "settings"} credentialVersion={credentialVersion} coursePanelRef={setCoursePanel}
          onReviewAssignments={openAssignmentReview}
          onTokenRemoved={() => {
            setBCoursesCredentialVersion((version) => version + 1);
            setSetupNotice("");
          }}
          onSetup={(provider) => { setSetupNotice(""); setSetup({ provider }); }}
          onSyncSettled={() => { void retry(); void planning.refresh(); }} />
        {setupNotice ? <p role="status">{setupNotice}</p> : null}
        {screen === "settings" && setup ? <ConnectionSetup provider={setup.provider} onDismiss={() => setSetup(null)} onSaved={(notice) => {
          setCredentialVersion((version) => version + 1);
          if (setup.provider === "bCourses") setBCoursesCredentialVersion((version) => version + 1);
          setSetupNotice(notice ?? (setup.provider === "bCourses" ? "bCourses accepted your token. Open Manage courses to choose courses or refresh assignments." : "Google sign-in file saved. Open Google to check sign-in status."));
          setSetup((current) => current === setup ? null : current);
        }} /> : null}
      </section>

      <div hidden={screen !== "plan"}>

      {loadError ? (
        <p className="error load-error" role="alert">
          {loadError}{" "}
          <button type="button" className="link" onClick={() => void retry()}>
            Try again
          </button>
        </p>
      ) : null}

      <nav className="plan-navigation" aria-label="Plan views">
        <button type="button" aria-pressed={planView === "today"} onClick={() => setPlanView("today")}>Today</button>
        <button type="button" aria-pressed={planView === "week"} onClick={() => setPlanView("week")}>Week</button>
        <button type="button" aria-pressed={planView === "projects"} onClick={() => setPlanView("projects")}>Projects</button>
      </nav>
      {pendingCapture ? <section aria-label="Pending task save"><p role="status">A task save needs confirmation: {pendingCapture.title}.</p>
        <button type="button" onClick={() => setReviewPendingCapture(value => !value)} aria-expanded={reviewPendingCapture}>Review pending task save</button>
        {reviewPendingCapture ? <div>
          <h2>Review pending task save</h2>
          <p className="muted">{projects?.find(project => project.id === pendingCapture.project_id)?.name ?? "Project unavailable"}</p>
          <TaskCaptureForm key={pendingCapture.operation_id} projectId={pendingCapture.project_id!}
            onCancel={() => setReviewPendingCapture(false)}
            onSaved={() => { setReviewPendingCapture(false); void run(async () => {}, "Task added.").catch(() => setStatus("Task saved. Refresh your views to see it.")); }} />
        </div> : null}
      </section> : null}
      <div hidden={planView !== "today"}>
      <Today visible={screen === "plan" && planView === "today"} lastSessionId={timer.state?.last_session?.id ?? null} plan={planning.plan} projects={projects ?? []} loading={planning.loading} error={planning.error} locked={mutations > 0 || planning.loading || Boolean(loadError) || Boolean(planning.error)} onRun={run} onTrack={openTrack} onRetry={() => void planning.refresh()} />
      </div>

      <div className="workspace plan-workspace" hidden={planView === "today"}>
        <div className="work-list" hidden={planView !== "projects"}>
          <section className="projects" aria-labelledby="projects-heading">
            <h2 id="projects-heading">Projects</h2>
            {projects === null && !loadError ? <p className="muted">Loading…</p> : null}
            {projects !== null ? (
              <>
                <div className="project-actions">
                  {selected ? (
                    renaming ? (
                      <TextForm
                        key={`rename-${selected.id}-${selected.revision}`}
                        label={`Rename “${selected.name}”`}
                        placeholder="New name"
                        submitLabel="Save name"
                        initial={selected.name}
                        maxLength={NAME_MAX_LENGTH}
                        onCancel={() => { setRenaming(false); requestAnimationFrame(() => renameProjectTrigger.current?.focus()); }}
                        onSubmit={async (name) => {
                          const updated = await renameProject(selected.id, name);
                          setProjects((current) => (current ?? []).map((p) => (p.id === updated.id ? updated : p)));
                          setRenaming(false);
                          setStatus(`Renamed to “${updated.name}”.`);
                          requestAnimationFrame(() => renameProjectTrigger.current?.focus());
                        }}
                      />
                    ) : (
                      <button ref={renameProjectTrigger} type="button" className="link" onClick={() => setRenaming(true)}>
                        Rename “{selected.name}”
                      </button>
                    )
                  ) : null}
                  <button ref={addProjectTrigger} type="button" className="link" aria-expanded={addingProject} disabled={savingProject} onClick={() => setAddingProject((open) => !open)}>
                    + Add project
                  </button>
                  {addingProject ? <TextForm
                    label="New project"
                    placeholder="Add a project"
                    submitLabel="Add project"
                    maxLength={NAME_MAX_LENGTH}
                    onCancel={() => { setAddingProject(false); addProjectTrigger.current?.focus(); }}
                    onSubmit={async (name) => {
                      setSavingProject(true);
                      try {
                        const project = await createProject(name);
                        setProjects((current) => [...(current ?? []), project]);
                        setSelectedId(project.id);
                        setAddingProject(false);
                        setStatus(`Added project “${project.name}”.`);
                        requestAnimationFrame(() => addProjectTrigger.current?.focus());
                      } finally {
                        setSavingProject(false);
                      }
                    }}
                  /> : null}
                </div>
                <ul className="project-list">
                  {projects.map((project) => (
                    <li key={project.id}>
                      <button
                        type="button"
                        className={project.id === selectedId ? "chip chip-on" : "chip"}
                        aria-current={project.id === selectedId ? "true" : undefined}
                        onClick={() => setSelectedId(project.id)}
                      >
                        {project.name}
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </section>

          {selected ? (
            <section className="tasks-section" aria-labelledby="tasks-heading">
              <h2 ref={tasksHeading} tabIndex={-1} id="tasks-heading">{selected.name}</h2>
              {progress ? <p className="muted">{progress.completed} of {progress.total} work items complete</p> : null}

              {!taskDraftProjects.includes(selected.id) ? (
                <button ref={addTaskTrigger} type="button" aria-expanded="false" disabled={tasks === null || Boolean(loadError)} onClick={() => setTaskDraftProjects((ids) => [...ids, selected.id])}>+ Add task</button>
              ) : null}
              {taskDraftProjects.map((projectId) => (
                <div key={projectId} hidden={selected.id !== projectId}>
                  <TaskCaptureForm
                    projectId={projectId}
                    onCancel={(resolvedElsewhere) => {
                      setTaskDraftProjects((ids) => ids.filter((id) => id !== projectId));
                      if (resolvedElsewhere && selectedIdRef.current === projectId) {
                        setTasks(null);
                        setProgress(null);
                        void refreshTasks(projectId);
                        void planning.refresh();
                      }
                      requestAnimationFrame(() => {
                        if (selectedIdRef.current !== projectId) return;
                        if (resolvedElsewhere) tasksHeading.current?.focus();
                        else addTaskTrigger.current?.focus();
                      });
                    }}
                    onSaved={() => {
                      setTaskDraftProjects((ids) => ids.filter((id) => id !== projectId));
                      if (selectedIdRef.current === projectId) requestAnimationFrame(() => addTaskTrigger.current?.focus());
                      void run(async () => {}, "Task added.").catch(() => setStatus("Task saved. Refresh your views to see it."));
                    }}
                  />
                </div>
              ))}

              {tasks === null && !loadError ? <p className="muted">Loading…</p> : null}
              {tasks !== null && parents.length === 0 ? <p className="muted">No tasks in this project yet.</p> : null}

              <ul className="tasks" aria-label={`Tasks in ${selected.name}`}>
                {parents.map((task) => {
                  const children = subtasksOf(task.id);
                  return (
                    <li key={task.id} className="task">
                      <TaskRow
                        task={task}
                        onToggle={(complete) =>
                          run(() => setTaskCompletion(task.id, complete), complete ? "Marked complete." : "Reopened.")
                        }
                        onEdit={() => setEditing(editing === task.id ? null : task.id)}
                        editing={editing === task.id}
                        locked={mutations > 0 || Boolean(loadError) || Boolean(planning.error)}
                        planning={<TaskPlanning task={task} plan={planning.plan} selectedDay={planning.selectedDay} onRun={run} />}
                        onTrack={() => openTrack(task.id)}
                        extra={
                          <button type="button" className="link" onClick={() => setAddingSubtaskTo(addingSubtaskTo === task.id ? null : task.id)}>
                            {addingSubtaskTo === task.id ? "Cancel subtask" : "Add subtask"}
                          </button>
                        }
                      />

                      {editing === task.id ? (
                        <TaskForm
                          task={task}
                          submitLabel="Save changes"
                          onCancel={() => setEditing(null)}
                          onSubmit={async (edit) => {
                            await run(() => updateTask(task.id, edit), "Changes saved.");
                            setEditing((current) => current === task.id ? null : current);
                          }}
                        />
                      ) : null}

                      {addingSubtaskTo === task.id ? (
                        <TaskForm
                          submitLabel="Add subtask"
                          onCancel={() => setAddingSubtaskTo(null)}
                          onSubmit={async (edit) => {
                            await run(() => createTask({ ...edit, title: edit.title ?? "", parent_id: task.id }), "Subtask added.");
                            setAddingSubtaskTo(null);
                          }}
                        />
                      ) : null}

                      {children.length ? (
                        <ul className="subtasks">
                          {children.map((child) => (
                            <li key={child.id} className="task">
                              <TaskRow
                                task={child}
                                onToggle={(complete) =>
                                  run(() => setTaskCompletion(child.id, complete), complete ? "Marked complete." : "Reopened.")
                                }
                                onEdit={() => setEditing(editing === child.id ? null : child.id)}
                                editing={editing === child.id}
                                locked={mutations > 0 || Boolean(loadError) || Boolean(planning.error)}
                                planning={<TaskPlanning task={child} plan={planning.plan} selectedDay={planning.selectedDay} onRun={run} />}
                                onTrack={() => openTrack(child.id)}
                              />
                              {editing === child.id ? (
                                <TaskForm
                                  task={child}
                                  submitLabel="Save changes"
                                  onRemove={async () => {
                                    await run(() => removeSubtask(child.id), "Subtask removed.");
                                    setEditing(null);
                                  }}
                                  onCancel={() => setEditing(null)}
                                  onSubmit={async (edit) => {
                                    await run(() => updateTask(child.id, edit), "Changes saved.");
                                    setEditing((current) => current === child.id ? null : current);
                                  }}
                                />
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </section>
          ) : null}
        </div>
      <div hidden={planView !== "week"}><WeeklyPlanner state={planning} projects={projects ?? []} onRun={run} locked={mutations > 0 || planning.loading || Boolean(loadError) || Boolean(planning.error)} onTrack={openTrack} /></div>
      </div>

      </div>

      <p className="status" role="status" aria-live="polite">{status}</p>
    </main>
  );
}

function TaskRow({
  task,
  onToggle,
  onEdit,
  editing,
  extra,
  planning,
  locked,
  onTrack,
}: {
  task: Task;
  onToggle: (complete: boolean) => Promise<void>;
  onEdit: () => void;
  editing: boolean;
  extra?: ReactNode;
  planning?: ReactNode;
  locked: boolean;
  onTrack: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const checkboxRef = useRef<HTMLInputElement>(null);
  const derived = task.subtask_count > 0;
  const compact = task.completed && !derived;
  const hint = derived
    ? `Complete when all ${task.subtask_count} subtasks are. ${task.completed_subtask_count} of ${task.subtask_count} done.`
    : undefined;

  return (
    <div className={task.completed ? "task-row task-done" : "task-row"}>
      <input
        type="checkbox"
        ref={checkboxRef}
        id={`done-${task.id}`}
        checked={task.completed}
        disabled={derived || busy || locked}
        title={hint}
        aria-describedby={derived ? `derived-${task.id}` : undefined}
        onChange={async (event) => {
          const restoreFocus = document.activeElement === event.currentTarget;
          setBusy(true);
          setError(null);
          try {
            await onToggle(event.target.checked);
          } catch (caught) {
            setError(errorMessage(caught));
          } finally {
            setBusy(false);
            if (restoreFocus) requestAnimationFrame(() => {
              if (document.activeElement === document.body) checkboxRef.current?.focus();
            });
          }
        }}
      />
      <div className="task-main">
        <label htmlFor={`done-${task.id}`} className="task-title">{task.title}</label>
        {!compact ? <><p className="task-meta muted">
          {derived ? (
            <span id={`derived-${task.id}`}>{task.completed_subtask_count} of {task.subtask_count} subtasks done</span>
          ) : null}
          {task.deadline ? <span>Due {formatDeadline(task.deadline)}</span> : null}
          {task.estimate_minutes ? <span>{formatEstimate(task.estimate_minutes)}</span> : null}
        </p>
        {task.notes ? <p className="task-notes">{task.notes}</p> : null}
        {planning}</> : null}
        {error ? <p className="error" role="alert">{error}</p> : null}
      </div>
      {!compact ? <div className="task-actions">
        <StartTrackingButton task={task} onTrack={onTrack} disabled={busy || locked} />
        <button type="button" className="link" onClick={onEdit}>{editing ? "Cancel" : "Edit"}</button>
        {extra}
      </div> : null}
    </div>
  );
}

/** Create or edit a task. Submits only the fields the form actually carries. */
function TaskForm({
  task,
  submitLabel,
  onSubmit,
  onCancel,
  onRemove,
  autoFocusTitle = false,
}: {
  task?: Task;
  submitLabel: string;
  onSubmit: (edit: TaskEdit & { title?: string }) => Promise<void>;
  onCancel?: () => void;
  onRemove?: () => Promise<void>;
  autoFocusTitle?: boolean;
}) {
  const [title, setTitle] = useState(task?.title ?? "");
  const [notes, setNotes] = useState(task?.notes ?? "");
  const [deadline, setDeadline] = useState(task?.deadline ?? "");
  const [estimate, setEstimate] = useState(task?.estimate_minutes ? String(task.estimate_minutes) : "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmRemoval, setConfirmRemoval] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);
  // Several of these forms can be open at once, so ids must be unique per instance.
  const uid = useId();

  const trimmed = title.trim();
  // Count code points, as the service does, not the UTF-16 units maxLength would.
  const tooLong = [...trimmed].length > TITLE_MAX_LENGTH;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!trimmed || tooLong || busy) return;
    setBusy(true);
    setError(null);
    try {
      const estimateText = estimate.trim();
      const estimateNumber = Number(estimateText);
      await onSubmit({
        title: trimmed,
        notes: notes.trim() || null,
        deadline: deadline.trim() || null,
        // Empty clears the field. Anything that is not a whole number is passed through
        // unchanged so the service rejects it by name, rather than becoming JSON null
        // here and silently clearing the estimate instead.
        estimate_minutes:
          estimateText === ""
            ? null
            : Number.isInteger(estimateNumber)
              ? estimateNumber
              : (estimateText as unknown as number),
      });
      if (!task) {
        setTitle("");
        setNotes("");
        setDeadline("");
        setEstimate("");
        titleRef.current?.focus();
      }
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor={`title-${uid}`}>Title</label>
        <input
          id={`title-${uid}`}
          autoFocus={autoFocusTitle}
          ref={titleRef}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          aria-invalid={tooLong || error ? true : undefined}
          required
        />
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor={`deadline-${uid}`}>Deadline</label>
          <input
            id={`deadline-${uid}`}
            type="date"
            value={deadline}
            onChange={(event) => setDeadline(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor={`estimate-${uid}`}>Estimate (minutes)</label>
          <input
            id={`estimate-${uid}`}
            type="number"
            inputMode="numeric"
            min={ESTIMATE_MIN_MINUTES}
            max={ESTIMATE_MAX_MINUTES}
            value={estimate}
            onChange={(event) => setEstimate(event.target.value)}
          />
        </div>
      </div>
      <div className="field">
        <label htmlFor={`notes-${uid}`}>Notes</label>
        <textarea
          id={`notes-${uid}`}
          rows={2}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />
      </div>
      {tooLong ? <p className="error">Keep the title to {TITLE_MAX_LENGTH} characters or fewer.</p> : null}
      {error ? <p className="error" role="alert">{error}</p> : null}
      <div className="form-actions">
        <button type="submit" disabled={!trimmed || tooLong || busy}>{busy ? "Saving…" : submitLabel}</button>
        {onCancel ? <button type="button" className="link" disabled={busy} onClick={onCancel}>Cancel</button> : null}
        {onRemove ? (
          <button type="button" className="link" disabled={busy} onClick={() => setConfirmRemoval(true)}>
            Remove subtask
          </button>
        ) : null}
      </div>
      {confirmRemoval && onRemove ? (
        <div>
          <p>Remove this subtask permanently? Removing the last subtask leaves its parent incomplete.</p>
          <button type="button" disabled={busy} onClick={async () => {
            setBusy(true);
            setError(null);
            try { await onRemove(); }
            catch (caught) { setError(errorMessage(caught)); }
            finally { setBusy(false); }
          }}>Confirm removal</button>{" "}
          <button type="button" className="link" disabled={busy} onClick={() => setConfirmRemoval(false)}>Keep subtask</button>
        </div>
      ) : null}
    </form>
  );
}

/** A one-field form, used for creating and renaming projects. */
function TextForm({
  label,
  placeholder,
  submitLabel,
  initial = "",
  maxLength,
  onSubmit,
  onCancel,
}: {
  label: string;
  placeholder: string;
  submitLabel: string;
  initial?: string;
  maxLength: number;
  onSubmit: (value: string) => Promise<void>;
  onCancel?: () => void;
}) {
  const [value, setValue] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const trimmed = value.trim();
  const tooLong = [...trimmed].length > maxLength;
  const id = useId();

  return (
    <form
      className="text-form"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!trimmed || tooLong || busy) return;
        setBusy(true);
        setError(null);
        try {
          await onSubmit(trimmed);
          if (!initial) setValue("");
        } catch (caught) {
          setError(errorMessage(caught));
        } finally {
          setBusy(false);
        }
      }}
    >
      <label htmlFor={id}>{label}</label>
      <div className="field-row">
        <input autoFocus id={id} value={value} placeholder={placeholder} maxLength={maxLength * 2} onChange={(event) => setValue(event.target.value)} />
        <button type="submit" disabled={!trimmed || tooLong || busy}>{submitLabel}</button>
        {onCancel ? <button type="button" className="link" disabled={busy} onClick={onCancel}>Cancel</button> : null}
      </div>
      {tooLong ? <p className="error">Keep this to {maxLength} characters or fewer.</p> : null}
      {error ? <p className="error" role="alert">{error}</p> : null}
    </form>
  );
}
