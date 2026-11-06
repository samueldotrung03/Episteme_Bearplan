import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError, checkBCoursesToken, getBCourses, getConnections, getGoogle, removeBCoursesToken, setGoogleSyncPaused, syncGoogleTasks,
  type BCoursesState, type ConnectionsState, type GoogleState,
} from "./api";
import { ConnectionDialog, type SetupProvider } from "./ConnectionSetup";

const stamp = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
const time = (value: string) => stamp.format(new Date(value));
const errorText = (error: unknown, fallback: string) => error instanceof ApiError ? error.message : fallback;

type SyncAction = "pause" | "resume" | "sync";

export function ConnectionPanels({ visible, credentialVersion, onSetup, onSynced, onTokenRemoved }: {
  visible: boolean;
  credentialVersion: number;
  onSetup: (provider: SetupProvider) => void;
  onSynced: () => void;
  onTokenRemoved: () => void;
}) {
  const [credentials, setCredentials] = useState<ConnectionsState | null>(null);
  const [courses, setCourses] = useState<BCoursesState | null>(null);
  const [google, setGoogle] = useState<GoogleState | null>(null);
  const [credentialError, setCredentialError] = useState("");
  const [coursesError, setCoursesError] = useState("");
  const [googleError, setGoogleError] = useState("");
  const [actionError, setActionError] = useState("");
  const [receipt, setReceipt] = useState("");
  const [action, setAction] = useState<SyncAction | null>(null);
  const actionPending = useRef(false);
  const googleRead = useRef<AbortController | null>(null);
  const [tokenAction, setTokenAction] = useState<"check" | "remove" | null>(null);
  const [tokenError, setTokenError] = useState("");
  const [removeError, setRemoveError] = useState("");
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [removed, setRemoved] = useState(false);
  const tokenPending = useRef(false);
  const credentialRead = useRef<AbortController | null>(null);
  const setupToken = useRef<HTMLButtonElement>(null);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    if (!visible) return;
    const controller = new AbortController();
    const { signal } = controller;
    const setupRead = new AbortController();
    credentialRead.current = setupRead;
    if (!tokenPending.current) void getConnections(setupRead.signal).then((next) => {
      if (setupRead.signal.aborted) return;
      setCredentials(next);
      setCredentialError("");
    }, (error) => {
      if (!setupRead.signal.aborted) setCredentialError(errorText(error, "Could not read saved setup."));
    });
    void getBCourses(signal).then((next) => {
      if (signal.aborted) return;
      setCourses(next);
      setCoursesError("");
    }, (error) => {
      if (!signal.aborted) setCoursesError(errorText(error, "Could not read bCourses refresh status."));
    });
    return () => { setupRead.abort(); controller.abort(); };
  }, [visible, credentialVersion, retry]);

  const readGoogle = useCallback(async () => {
    if (actionPending.current || googleRead.current) return;
    const controller = new AbortController();
    googleRead.current = controller;
    try {
      const next = await getGoogle(controller.signal);
      if (controller.signal.aborted) return;
      setGoogle(next);
      setGoogleError("");
    } catch (error) {
      if (!controller.signal.aborted) setGoogleError(errorText(error, "Could not read Google status."));
    } finally {
      if (googleRead.current === controller) googleRead.current = null;
    }
  }, []);

  useEffect(() => {
    if (!visible) return;
    void readGoogle();
    const timer = window.setInterval(() => void readGoogle(), 3000);
    return () => {
      window.clearInterval(timer);
      googleRead.current?.abort();
      googleRead.current = null;
    };
  }, [visible, credentialVersion, retry, readGoogle]);

  async function run(nextAction: SyncAction) {
    if (actionPending.current) return;
    actionPending.current = true;
    googleRead.current?.abort();
    googleRead.current = null;
    setAction(nextAction);
    setActionError("");
    setReceipt("");
    try {
      const next = await (nextAction === "sync" ? syncGoogleTasks() : setGoogleSyncPaused(nextAction === "pause"));
      setGoogle(next);
      setGoogleError("");
      if (nextAction === "sync") {
        onSynced();
        setReceipt("Google sync finished.");
      }
    } catch (error) {
      setActionError(errorText(error, "Could not confirm the Google action. Check the current status and try again."));
    } finally {
      actionPending.current = false;
      setAction(null);
    }
  }

  useEffect(() => {
    if (removed && setupToken.current?.closest('[hidden]') === null) setupToken.current.focus();
  }, [removed]);

  function dismissRemoval() {
    setConfirmRemove(false);
    if (removeError) setRetry((value) => value + 1);
    setRemoveError("");
  }

  async function runToken(nextAction: "check" | "remove") {
    if (tokenPending.current) return;
    tokenPending.current = true;
    credentialRead.current?.abort();
    setTokenAction(nextAction);
    setTokenError("");
    setRemoveError("");
    setRemoved(false);
    try {
      const next = await (nextAction === "check" ? checkBCoursesToken() : removeBCoursesToken());
      setCredentials(next);
      setCredentialError("");
      if (nextAction === "remove") {
        setConfirmRemove(false);
        setRemoved(!next.bcourses.set);
        onTokenRemoved();
      }
    } catch (error) {
      if (nextAction === "check") {
        setTokenError(`Check could not be confirmed. ${errorText(error, "Try checking again.")}`);
      } else {
        setRemoveError(`Removal could not be confirmed. ${errorText(error, "Retry or choose Keep token to refresh the status.")}`);
      }
    } finally {
      tokenPending.current = false;
      setTokenAction(null);
    }
  }

  const token = credentials?.bcourses;
  const courseSync = courses?.sync;
  const paused = Boolean(google?.tasks.paused_at);
  const accountReview = google?.tasks.account_status === "different_account" || google?.tasks.account_status === "unowned_links";
  const controlsBusy = Boolean(action || googleError || google?.connection_changing || google?.pausing || google?.sign_in_pending);
  const showGoogleControls = Boolean(google?.configured && google.connected);
  return <>
    <ul className="settings-connections">
      <li>
        <h4>bCourses</h4>
        <p>{token ? (token.set ? "Token saved" : "Setup needed") : credentialError ? "Setup status unavailable" : "Checking setup…"}</p>
        {token?.set && token.checked_at ? <p className="muted">{token.check_ok ? "Last check accepted" : "Last check rejected"} · {time(token.checked_at)}</p> : null}
        {token?.check_ok === false && token.check_message ? <p role="alert" className="error">{token.check_message}</p> : null}
        {courseSync ? <p className="muted">{courseSync.last_success_at ? `Last assignment refresh ${time(courseSync.last_success_at)}` : "No successful assignment refresh recorded."}</p> : null}
        {courseSync?.last_error ? <p role="alert" className="error">Last refresh failed. {courseSync.last_error}</p> : null}
        {credentialError ? <p role="alert" className="error">Could not refresh setup status. {credentialError}</p> : null}
        {coursesError ? <p role="alert" className="error">Could not refresh assignment status. {coursesError}</p> : null}
        {tokenError && token?.set ? <p role="alert" className="error">{tokenError}</p> : null}
        {tokenAction === "check" ? <p role="status">Checking saved token…</p> : null}
        {removed && !token?.set ? <p role="status">bCourses token removed from BearPlans.</p> : null}
        <div className="form-actions connection-actions">
          <a href="#bcourses">Open bCourses</a>
          <button ref={setupToken} type="button" className="secondary" disabled={Boolean(tokenAction)}
            onClick={() => { setTokenError(""); setRemoved(false); onSetup("bCourses"); }}>
            {token?.set ? "Replace bCourses token" : "Set up or replace bCourses token"}
          </button>
          {token?.set ? <>
            <button type="button" className="secondary" disabled={Boolean(tokenAction || credentialError)}
              onClick={() => void runToken("check")}>Check saved token</button>
            <button type="button" className="secondary" disabled={Boolean(tokenAction || credentialError)}
              onClick={() => setConfirmRemove(true)}>Remove token…</button>
          </> : null}
        </div>
      </li>
      <li>
        <h4>Google</h4>
        <p>{google ? (google.setup === "configured" ? "Desktop sign-in file saved" : google.setup === "unusable" ? "Sign-in file needs replacement" : "Setup needed") : googleError ? "Setup status unavailable" : "Checking setup…"}</p>
        {google?.configured ? <p>{google.sign_in_pending ? "Waiting for Google sign-in" : google.connected ? "Sign-in saved" : "Sign-in needed"}</p> : null}
        {google?.sign_in_error ? <p role="alert" className="error">{google.sign_in_error}</p> : null}
        {google?.missing_permissions.length ? <p role="alert" className="error">Some permissions are missing. Open Google to reconnect.</p> : null}
        {accountReview ? <p role="alert" className="error">Google needs an account review before it can sync.</p> : null}
        {google?.tasks.last_error ? <p role="alert" className="error">Last sync failed. {google.tasks.last_error}</p> : null}
        {googleError ? <p role="alert" className="error">Could not refresh Google status. {googleError}</p> : null}
        {actionError ? <p role="alert" className="error">{actionError}</p> : null}
        {google?.configured ? <p className="muted">{google.tasks.last_success_at ? `Last full sync ${time(google.tasks.last_success_at)}` : "No successful full sync recorded."}</p> : null}
        {action === "pause" || google?.pausing ? <p role="status">Pausing automatic sync…</p>
          : action === "resume" ? <p role="status">Resuming automatic sync…</p>
          : google?.connection_changing ? <p role="status">Updating Google connection…</p>
          : null}
        {showGoogleControls ? <>
          <p role="status">{paused ? "Automatic sync is paused." : "Automatic sync is enabled."}</p>
          {action === "sync" || google?.activity === "syncing" ? <p role="status">Syncing with Google…</p>
            : google?.activity === "refreshing_calendars" ? <p role="status">Refreshing calendars…</p> : null}
          {receipt ? <p role="status">{receipt}</p> : null}
          <div className="form-actions connection-actions">
            <button type="button" disabled={controlsBusy} onClick={() => void run(paused ? "resume" : "pause")}>{paused ? "Resume automatic sync" : "Pause automatic sync"}</button>
            <button type="button" className="secondary" disabled={controlsBusy || accountReview || google?.activity !== "idle"}
              onClick={() => void run("sync")}>{paused ? "Sync once" : "Sync now"}</button>
          </div>
        </> : null}
        <div className="form-actions connection-actions">
          <a href="#google">Open Google</a>
          <button type="button" className="secondary" disabled={Boolean(action || google?.connection_changing || google?.pausing || google?.sign_in_pending)} onClick={() => onSetup("Google")}>Set up or replace Google sign-in file</button>
        </div>
      </li>
    </ul>
    {visible && confirmRemove ? <ConnectionDialog title="Remove bCourses token?" busy={tokenAction === "remove"} onDismiss={dismissRemoval}>
      <p>BearPlans will stop refreshing assignments until you save another token. Course selections, cached assignments and tasks you added will stay.</p>
      <p className="muted">To revoke the token in bCourses, use your bCourses account settings.</p>
      {removeError ? <p className="error" role="alert">{removeError}</p> : null}
      <div className="form-actions">
        <button type="button" className="secondary" autoFocus disabled={tokenAction === "remove"} onClick={dismissRemoval}>Keep token</button>
        <button type="button" disabled={tokenAction === "remove"} onClick={() => void runToken("remove")}>Remove token</button>
      </div>
      {tokenAction === "remove" ? <p role="status">Removing saved token…</p> : null}
    </ConnectionDialog> : null}
    {credentialError || coursesError || googleError
      ? <button type="button" className="secondary" onClick={() => setRetry((value) => value + 1)}>Retry connection status</button>
      : null}
  </>;
}
