import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, cancelGoogleSignIn, connectGoogle, disconnectGoogle, followGoogleCalendars, getGoogle, getGoogleCalendars, getGoogleChanges, refreshGoogleCalendars, resolveGoogleCreate, syncGoogleTasks, useGoogleAccount, verifyGoogleCreate, type GoogleCalendar, type GoogleState } from "./api";

import { ConnectionDialog } from "./ConnectionSetup";

const stampLabel = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
const message = (caught: unknown, fallback: string) => caught instanceof ApiError ? caught.message : fallback;

export function Google({ visible, onChanged, onOpenSettings }: { visible: boolean; onChanged?: () => void; onOpenSettings?: React.MouseEventHandler<HTMLAnchorElement> }) {
  const [state, setState] = useState<GoogleState | null>(null);
  const [statusReadThisVisit, setStatusReadThisVisit] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [readError, setReadError] = useState<string | null>(null);
  const [calendarError, setCalendarError] = useState<string | null>(null);
  const [reviewingScope, setReviewingScope] = useState(false);
  const [recovery, setRecovery] = useState<{ kind: "disconnect" } | { kind: "account"; key: string } | { kind: "create"; key: string } | null>(null);
  const [signInLink, setSignInLink] = useState<{ url: string; attempt_id: string } | null>(null);
  const [status, setStatus] = useState("");
  const viewVisible = useRef(visible);
  const statusRead = useRef<AbortController | null>(null);
  const calendarRead = useRef<AbortController | null>(null);
  const actionRunning = useRef(false);
  const [calendars, setCalendars] = useState<GoogleCalendar[]>([]);
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const acceptCalendars = useCallback((list: GoogleCalendar[]) => {
    setCalendars(list);
    setChosen(new Set(list.filter((calendar) => calendar.followed).map((calendar) => calendar.calendar_id)));
  }, []);

  const load = useCallback(async () => {
    if (!viewVisible.current) return;
    statusRead.current?.abort();
    const controller = new AbortController();
    statusRead.current = controller;
    try {
      const next = await getGoogle(controller.signal);
      if (controller.signal.aborted) return;
      setState(next);
      setSignInLink((link) => link?.attempt_id === next.sign_in_attempt_id ? link : null);
      setStatusReadThisVisit(true);
      setReadError(null);
    } catch (caught) {
      if (!controller.signal.aborted) setReadError(message(caught, "Could not read the Google connection."));
    } finally {
      if (statusRead.current === controller) statusRead.current = null;
    }
  }, []);

  useEffect(() => {
    viewVisible.current = visible;
    if (!visible) {
      setStatusReadThisVisit(false);
      setReviewingScope(false);
      setRecovery(null);
      return;
    }
    if (!actionRunning.current) void load();
    return () => {
      viewVisible.current = false;
      statusRead.current?.abort();
    };
  }, [visible, load]);

  const connected = state?.connected ?? false;
  const pending = state?.sign_in_pending ?? false;
  const pendingAttemptId = state?.sign_in_attempt_id;
  const tasks = state?.tasks;
  const paused = Boolean(tasks?.paused_at);
  const pausing = state?.pausing ?? false;
  const reviewRequired = tasks?.account_status === "different_account" || tasks?.account_status === "unowned_links";
  const accountReviewKey = tasks?.account_review_key;
  const uncertainCreate = tasks?.pending_create;
  const changing = state?.connection_changing ?? false;
  const providerBusy = changing || pausing || (state?.activity ?? "idle") !== "idle";
  const controlsBusy = busy !== null || providerBusy;
  const canConnect = Boolean(state?.configured && statusReadThisVisit && !readError && !pending && !controlsBusy);

  // Read the saved picker state. Preserve the existing first-visit refresh.
  useEffect(() => {
    if (!visible) return;
    acceptCalendars([]);
    setCalendarError(null);
    if (!statusReadThisVisit || !connected || pending || changing || reviewRequired) return;
    const controller = new AbortController();
    calendarRead.current = controller;
    void (async () => {
      try {
        const saved = await getGoogleCalendars(controller.signal);
        if (controller.signal.aborted) return;
        const list = saved.length || paused || pausing ? saved : await refreshGoogleCalendars({ automatic: true, signal: controller.signal });
        if (!controller.signal.aborted) {
          acceptCalendars(list);
          if (!saved.length && !paused && !pausing && !actionRunning.current) void load();
        }
      } catch (caught) {
        if (!controller.signal.aborted) {
          setCalendarError(message(caught, "Could not read your Google calendars."));
          if (!actionRunning.current) void load();
        }
      }
    })();
    return () => controller.abort();
  }, [visible, statusReadThisVisit, connected, pending, paused, pausing, changing, reviewRequired, acceptCalendars, load]);

  // Poll active backend work without overlapping status reads or local actions.
  useEffect(() => {
    if (!visible || (!pending && !providerBusy)) return;
    const timer = window.setInterval(() => {
      if (!actionRunning.current && !statusRead.current) void load();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [visible, pending, providerBusy, load]);

  const run = async (label: string, action: () => Promise<GoogleState | void>, done = "") => {
    if (actionRunning.current) return;
    actionRunning.current = true;
    statusRead.current?.abort();
    if (label === "follow" || label === "calendars") {
      calendarRead.current?.abort();
      setCalendarError(null);
    }
    setBusy(label);
    setError(null);
    setStatus("");
    try {
      const next = await action();
      if (next) {
        setState(next);
        setStatusReadThisVisit(viewVisible.current);
        setReadError(null);
      } else {
        await load();
      }
      if (done) setStatus(done);
    } catch (caught) {
      setError(message(caught, "Could not confirm the Google action. Check the connection and try again."));
      await load();
    } finally {
      actionRunning.current = false;
      setBusy(null);
    }
  };

  const connect = () => run("connect", async () => {
    const attempt = await connectGoogle();
    setSignInLink(attempt);
    setState((current) => current ? { ...current, sign_in_pending: true, sign_in_attempt_id: attempt.attempt_id } : current);
    try { window.open(attempt.url, "_blank", "noopener"); } catch { /* the explicit link is still available */ }
  }, "Finish signing in to Google, then return here.");

  const cancelSignIn = (attemptId: string) => run("cancel", async () => {
    const { cancelled } = await cancelGoogleSignIn(attemptId);
    setSignInLink(null);
    setState((current) => current && current.sign_in_attempt_id === attemptId
      ? { ...current, sign_in_pending: false, sign_in_attempt_id: null }
      : current);
    setStatus(cancelled ? "Google sign-in cancelled." : "That sign-in attempt is no longer waiting. Check the current status below.");
  });

  const disconnect = () => run("disconnect", async () => {
    const next = await disconnectGoogle();
    setStatus(next.revoked === false
      ? "Disconnected here. BearPlans could not confirm that Google revoked access."
      : next.revoked === true ? "Disconnected here. Google confirmed access was revoked." : "Disconnected here.");
    setRecovery(null);
    onChanged?.();
    return next;
  });

  const adoptAccount = (key: string) => run("account", async () => {
    const next = await useGoogleAccount(key);
    setRecovery(null);
    onChanged?.();
    return next;
  }, "Google account updated. Sync will create new links for this account.");

  const resolveCreate = (key: string) => run("create", async () => {
    const next = await resolveGoogleCreate(key);
    setRecovery(null);
    return next;
  }, "Review saved. A future sync may create a new Google copy.");

  const sync = () => run("sync", async () => {
    try {
      return await syncGoogleTasks();
    } finally {
      onChanged?.();
    }
  }, "Google sync finished.");

  return <section hidden={!visible} className="google" aria-label="Google" aria-busy={busy !== null}>
    <div className="forest-heading"><h2>Google</h2>
      <button type="button" disabled={controlsBusy || !connected || pending || reviewRequired || Boolean(uncertainCreate || tasks?.pending_create_unverified)} onClick={() => void sync()}>
        {busy === "sync" ? "Syncing…" : paused ? "Sync once" : "Sync now"}</button>
    </div>
    <p className="muted">Every project, task and subtask is copied to Google Tasks: each project becomes a list with the same name. Checking or unchecking a task with no subtasks in Google can update it here. Other changes made in Google are replaced by BearPlans. Your own Google lists are never touched.</p>
    {error && !recovery ? <p role="alert" className="error">{error}</p> : null}
    {readError ? <div className="form-actions">
      <p role="alert" className="error">Connection status could not be refreshed. {readError}</p>
      <button type="button" disabled={busy !== null} onClick={() => void load()}>Retry status</button>
    </div> : null}
    {status ? <p role="status">{status}</p> : null}

    {state?.setup === "unusable" ? <p role="alert" className="error">BearPlans could not use the saved Google Desktop sign-in file. <a href="#settings" onClick={onOpenSettings}>Open Settings</a> to replace it.</p> : null}
    {state?.setup === "missing" ? <p className="google-setup">No Google sign-in file was found. <a href="#settings" onClick={onOpenSettings}>Open Settings</a> to add one.</p> : null}
    {state?.configured ? <div className="google-connection">
      <p>{pending ? "Waiting for you to finish signing in…" : connected ? "Google sign-in is saved." : "Sign in to Google to continue."}</p>
      {changing ? <p>Updating the Google connection…</p>
        : state.activity === "refreshing_calendars" ? <p>Refreshing calendars…</p>
        : state.activity === "syncing" && busy !== "sync" ? <p>Syncing with Google…</p> : null}
      {reviewRequired ? <p role="alert" className="error">{tasks?.account_status === "unowned_links"
        ? "The existing Google links need an account review before they can be used."
        : "This account cannot use the saved Google links. Reconnect with the previous account or review starting fresh."}</p> : null}
      {tasks?.pending_create_unverified && connected ? <>
        <p role="alert" className="error">A saved Google connection needs review. Verify this account to see the details.</p>
        <button type="button" className="secondary" disabled={controlsBusy || !statusReadThisVisit || Boolean(readError)}
          onClick={() => void run("verify", verifyGoogleCreate)}>Verify Google account</button>
      </> : null}
      {uncertainCreate ? <>
        <p role="alert" className="error">A Google {uncertainCreate.kind.replace("_", " ")} may have been created, but BearPlans could not confirm it. Review this before syncing again.</p>
        <button type="button" className="secondary" disabled={controlsBusy || !statusReadThisVisit || Boolean(readError)}
          onClick={() => { setError(null); setRecovery({ kind: "create", key: uncertainCreate.review_key }); }}>Review uncertain Google create…</button>
      </> : null}
      {state.sign_in_error ? <p role="alert" className="error">{state.sign_in_error}</p> : null}
      {state.missing_permissions.length ? <p role="alert" className="error">Some permissions were not given ({state.missing_permissions.join(", ")}). Choose Reconnect Google and tick every box.</p> : null}
      {pending ? <>
        {signInLink && signInLink.attempt_id === pendingAttemptId
          ? <p><a href={signInLink.url} target="_blank" rel="noopener noreferrer">Open Google sign-in</a> if the browser tab did not open.</p> : null}
        {pendingAttemptId ? <button type="button" disabled={busy !== null}
          onClick={() => void cancelSignIn(pendingAttemptId)}>Cancel sign-in</button> : null}
      </> : <button type="button" disabled={!canConnect} onClick={() => setReviewingScope(true)}>{state.connected || state.missing_permissions.length ? "Reconnect Google" : "Connect Google"}</button>}
      {connected && !pending && reviewRequired && accountReviewKey ? <button type="button" className="secondary"
        disabled={controlsBusy || !statusReadThisVisit || Boolean(readError)} onClick={() => {
          setError(null);
          setRecovery({ kind: "account", key: accountReviewKey });
        }}>Review using this account…</button> : null}
      {connected ? <button type="button" className="link" disabled={busy !== null || changing || Boolean(readError)}
        onClick={() => { setError(null); setRecovery({ kind: "disconnect" }); }}>Disconnect</button> : null}
    </div> : null}

    {visible && recovery ? <ConnectionDialog
      title={recovery.kind === "disconnect" ? "Disconnect Google?" : recovery.kind === "account" ? "Use this Google account?" : "Review uncertain Google create"}
      busy={busy !== null} onDismiss={() => setRecovery(null)}>
      {recovery.kind === "disconnect" ? <>
        <p>BearPlans will remove the saved Google sign-in here and stop Google sync. Your setup file, local work, and cached calendar events will stay. Copies already in Google will stay there.</p>
        <p>BearPlans will ask Google to revoke access and report whether Google confirms it.</p>
      </> : recovery.kind === "create" ? <>
        <p>Current local work (may have changed): <strong>{uncertainCreate?.context}</strong>. A copy may already exist in Google. Check your Google Tasks or BearPlans calendar before continuing. BearPlans cannot tell whether the earlier request succeeded.</p>
        <p>BearPlans will not link to any earlier copy or delete anything in Google. Check carefully before removing a copy yourself; matching names do not prove it is the same item. Continuing clears this local review, and a future sync may create a duplicate. {paused ? "Automatic sync stays paused." : "Automatic sync may run after you continue."}</p>
      </> : <>
        <p>BearPlans will clear the previous Google sync links, calendar selections, and cached calendar events here. Your tasks, including imported tasks, and your history will stay. Copies in the previous Google account will stay there.</p>
        <p>The next sync will create new Google Tasks lists for all local projects and publish timed plans to a separate BearPlans calendar in this account. {paused ? "Automatic sync stays paused." : "Automatic sync may start after you confirm."}</p>
      </>}
      {error ? <p role="alert" className="error">{error}</p> : null}
      <div className="form-actions">
        <button type="button" className="secondary" autoFocus disabled={busy !== null}
          onClick={() => setRecovery(null)}>Cancel</button>
        <button type="button" disabled={busy !== null || changing || Boolean(readError)
          || (recovery.kind === "account" && (!connected || pending || tasks?.account_review_key !== recovery.key))
          || (recovery.kind === "create" && (!connected || pending || uncertainCreate?.review_key !== recovery.key))}
          onClick={() => void (recovery.kind === "disconnect" ? disconnect() : recovery.kind === "account" ? adoptAccount(recovery.key) : resolveCreate(recovery.key))}>
          {recovery.kind === "disconnect" ? "Disconnect Google" : recovery.kind === "account" ? "Use this account" : "Continue after review"}
        </button>
      </div>
    </ConnectionDialog> : null}

    {visible && reviewingScope ? <ConnectionDialog title="What BearPlans shares with Google" busy={false}
      onDismiss={() => setReviewingScope(false)}>
      <ul className="google-sharing">
        <li><strong>Show calendar events in Plan.</strong> BearPlans reads the Google calendars you select. It leaves their events untouched.</li>
        <li><strong>Publish timed plans.</strong> Incomplete tasks with a planned start time sync to the separate BearPlans calendar with a 30-minute reminder.</li>
        <li><strong>Sync tasks.</strong> All local projects, tasks and subtasks sync to BearPlans-created Google Tasks lists, including bCourses assignments you added. Task titles, notes and dates are shared. Checking or unchecking an individual task or subtask in Google can update it here. Parent completion follows its subtasks. Your personal Google Tasks lists stay untouched.</li>
      </ul>
      <p className="muted">Calendar selection controls which events BearPlans reads. All local tasks are included in task sync.</p>
      <div className="form-actions">
        <button type="button" className="secondary" autoFocus onClick={() => setReviewingScope(false)}>Cancel</button>
        <button type="button" disabled={!canConnect} onClick={() => {
          setReviewingScope(false);
          void connect();
        }}>Continue with Google</button>
      </div>
    </ConnectionDialog> : null}

    {pausing ? <p role="status">Pausing… Waiting for current Google work to finish.</p>
      : paused ? <p>Automatic sync is paused.</p> : null}
    {tasks && connected ? <div className="google-tasks">
      <h3>Google Tasks</h3>
      {tasks.account_status === "verified" ? <p>{tasks.synced_tasks} {tasks.synced_tasks === 1 ? "task" : "tasks"} in {tasks.synced_lists} {tasks.synced_lists === 1 ? "list" : "lists"}.</p> : null}
      <p>{tasks.last_success_at ? `Last full sync succeeded ${stampLabel.format(new Date(tasks.last_success_at))}.` : "No successful full sync recorded."}</p>
      {tasks.last_error && tasks.last_error !== error ? <p role="alert" className="error">Last full sync failed: {tasks.last_error}</p> : null}
      <h3>Google Calendar</h3>
      {tasks.account_status === "verified" ? <p>{tasks.synced_events} upcoming {tasks.synced_events === 1 ? "event" : "events"} in the “BearPlans” calendar.</p> : null}
      <p className="muted">Give a planned task a start time (open it on the Plan screen, then “Move or remove”) and it appears in the BearPlans calendar with a reminder 30 minutes before. Finishing the task removes the event.</p>
      {!paused && !pausing && !reviewRequired ? <p className="muted">Automatic sync runs every two minutes and shortly after a change.</p> : null}
    </div> : null}

    {connected && !pending && !reviewRequired ? <div className="google-calendars">
      <h3>Calendars to show</h3>
      <p className="muted">Events from the calendars you tick appear beside each day on the Plan screen, where any event can be added as a task. BearPlans only reads these calendars. Changing your selection keeps tasks you already added and does not change which tasks sync to Google Tasks.</p>
      {paused && !pausing ? <p className="muted">Refresh calendars and Save calendars each contact Google once. Automatic sync stays paused.</p> : null}
      {calendarError ? <p role="alert" className="error">{calendarError}</p> : null}
      {calendars.length ? <fieldset disabled={controlsBusy}>
        <legend>Choose the calendars whose events you want to see</legend>
        {calendars.map((calendar) => <label key={calendar.calendar_id}>
          <input type="checkbox" checked={chosen.has(calendar.calendar_id)} onChange={(event) => setChosen((current) => {
            const next = new Set(current);
            if (event.target.checked) next.add(calendar.calendar_id); else next.delete(calendar.calendar_id);
            return next;
          })} />
          {calendar.color ? <span className="calendar-swatch" style={{ background: calendar.color }} aria-hidden="true" /> : null}
          {calendar.summary}{calendar.is_primary ? <span className="muted"> · main calendar</span> : null}
        </label>)}
      </fieldset> : <p className="muted">No calendars found yet.</p>}
      <div className="form-actions">
        <button type="button" disabled={controlsBusy || !calendars.length} onClick={() => void run("follow", async () => {
          acceptCalendars(await followGoogleCalendars(calendars[0].account_key, [...chosen]));
          onChanged?.();
        }, "Saved your calendars. Plan now shows events from your selection.")}>{busy === "follow" ? "Saving…" : "Save calendars"}</button>
        <button type="button" className="link" disabled={controlsBusy} onClick={() => void run("calendars", async () => {
          acceptCalendars(await refreshGoogleCalendars());
        }, "Updated your calendar list and events.")}>Refresh calendars</button>
      </div>
    </div> : null}
  </section>;
}

const CHANGE_CHECK_MS = 30000;

/** Calls onChange when a background Google sync changed something the page shows
 * (a task ticked in Google, followed-calendar events). Checks every 30 seconds while
 * the page is visible and when the window regains focus. */
export function useGoogleChanges(onChange: () => void) {
  const seen = useRef<number | null>(null);
  const callback = useRef(onChange);
  callback.current = onChange;
  useEffect(() => {
    const controller = new AbortController();
    let checking = false;
    const check = async () => {
      if (checking || document.visibilityState === "hidden") return;
      checking = true;
      try {
        const { version } = await getGoogleChanges(controller.signal);
        if (controller.signal.aborted) return;
        if (seen.current !== null && version !== seen.current) callback.current();
        seen.current = version;
      } catch { /* not connected or offline: try again later */ }
      finally { checking = false; }
    };
    void check();
    const timer = window.setInterval(() => { void check(); }, CHANGE_CHECK_MS);
    const onFocus = () => { void check(); };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onFocus);
    return () => {
      controller.abort();
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onFocus);
    };
  }, []);
}
