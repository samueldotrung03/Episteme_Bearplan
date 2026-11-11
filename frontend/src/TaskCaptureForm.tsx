import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { ESTIMATE_MAX_MINUTES, ESTIMATE_MIN_MINUTES, TITLE_MAX_LENGTH, type TaskCapture } from "./api";
import { checkCapture, readPendingCapture, resolveRejectedCapture, startCapture, retryCapture } from "./taskCaptureRecovery";

const message = (error: unknown) => error instanceof Error ? error.message : "Could not save. Try again.";
const notify = (origin: object) => window.dispatchEvent(new CustomEvent("bearplans-capture-change", { detail: origin }));

export function TaskCaptureForm({ projectId, onCancel, onSaved }: { projectId: string; onCancel: (resolvedElsewhere: boolean) => void; onSaved: () => void }) {
  const origin = useRef({});
  const [initial] = useState(() => { try { const pending = readPendingCapture(); return pending?.project_id === projectId ? pending : null; } catch { return null; } });
  const [title, setTitle] = useState(initial?.title ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [deadline, setDeadline] = useState(initial?.deadline ?? "");
  const [estimate, setEstimate] = useState(initial?.estimate_minutes == null ? "" : String(initial.estimate_minutes));
  const [day, setDay] = useState(initial?.planned_date ?? "");
  const [pending, setPending] = useState<TaskCapture | null>(initial);
  const [rejected, setRejected] = useState(false);
  const [resolvedElsewhere, setResolvedElsewhere] = useState(false);
  useEffect(() => {
    if (!pending) return;
    const checkOtherWindow = (event: Event) => {
      if (event instanceof CustomEvent && event.detail === origin.current) return;
      try {
        const current = readPendingCapture();
        if (!current || current.operation_id !== pending.operation_id) setResolvedElsewhere(true);
      } catch { /* Keep the form locked if recovery storage cannot be read. */ }
    };
    window.addEventListener("storage", checkOtherWindow);
    window.addEventListener("bearplans-capture-change", checkOtherWindow);
    return () => { window.removeEventListener("storage", checkOtherWindow); window.removeEventListener("bearplans-capture-change", checkOtherWindow); };
  }, [pending]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(initial ? "The previous save needs confirmation. Check its status before changing it." : null);
  const uid = useId();
  const locked = busy || resolvedElsewhere || (!!pending && !rejected);
  const validTitle = !!title.trim() && [...title.trim()].length <= TITLE_MAX_LENGTH;

  function saved() { setPending(null); setRejected(false); notify(origin.current); onSaved(); }
  function capture(): TaskCapture {
    return { operation_id: crypto.randomUUID(), project_id: projectId, title: title.trim(), notes: notes.trim() || null,
      deadline: deadline || null, estimate_minutes: estimate ? Number(estimate) : null, planned_date: day || null };
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || resolvedElsewhere || !validTitle || (pending && !rejected)) return;
    setBusy(true); setError(null);
    let attempted: TaskCapture | null = null;
    try {
      const next = capture();
      attempted = next;
      if (pending) {
        const resolution = await resolveRejectedCapture(pending.operation_id, next);
        if ("saved" in resolution) { saved(); return; }
        setPending(next); setRejected(false); notify(origin.current);
        await retryCapture(next.operation_id);
      } else await startCapture(next);
      saved();
    } catch (caught) {
      let stored: TaskCapture | null = null;
      try {
        stored = readPendingCapture();
        if (stored && (stored.operation_id === attempted?.operation_id || stored.operation_id === pending?.operation_id)) { setPending(stored); setRejected(false); }
      } catch { /* Keep unreadable recovery data untouched. */ }
      notify(origin.current);
      setError(`${message(caught)} ${stored && (stored.operation_id === attempted?.operation_id || stored.operation_id === pending?.operation_id) ? "Check the save status before changing the details." : stored ? "Review the other pending task save first." : "Your details are kept in this form."}`);
    } finally { setBusy(false); }
  }
  async function check() {
    if (!pending || busy || resolvedElsewhere) return;
    setBusy(true); setError(null);
    try {
      const result = await checkCapture(pending.operation_id);
      if ("saved" in result) saved();
      else { setRejected(true); setError(`${result.error.message} Your details are kept; edit them or cancel.`); }
    } catch (caught) { setError(`${message(caught)} Your request is kept; check again when the service is available.`); }
    finally { setBusy(false); }
  }
  async function cancel() {
    if (!pending || resolvedElsewhere) { onCancel(resolvedElsewhere); return; }
    if (!rejected || busy) return;
    setBusy(true); setError(null);
    try {
      const result = await resolveRejectedCapture(pending.operation_id, null);
      if ("saved" in result) saved();
      else { setPending(null); notify(origin.current); onCancel(false); }
    } catch (caught) { setRejected(false); setError(`${message(caught)} Your request is kept; check its status again.`); }
    finally { setBusy(false); }
  }
  return <form className="task-form" onSubmit={submit}>
    <div className="field"><label htmlFor={`capture-title-${uid}`}>Title</label><input autoFocus id={`capture-title-${uid}`} value={title} disabled={locked} onChange={e => setTitle(e.target.value)} required /></div>
    <div className="field-row">
      <div className="field"><label htmlFor={`capture-deadline-${uid}`}>Deadline</label><input id={`capture-deadline-${uid}`} type="date" value={deadline} disabled={locked} onChange={e => setDeadline(e.target.value)} /></div>
      <div className="field"><label htmlFor={`capture-estimate-${uid}`}>Estimate (minutes)</label><input id={`capture-estimate-${uid}`} type="number" min={ESTIMATE_MIN_MINUTES} max={ESTIMATE_MAX_MINUTES} value={estimate} disabled={locked} onChange={e => setEstimate(e.target.value)} /></div>
    </div>
    <div className="field"><label htmlFor={`capture-day-${uid}`}>Planned day</label><input id={`capture-day-${uid}`} type="date" value={day} disabled={locked} onChange={e => setDay(e.target.value)} /><span className="muted">Deadline and planned day are separate.</span></div>
    <div className="field"><label htmlFor={`capture-notes-${uid}`}>Notes</label><textarea id={`capture-notes-${uid}`} rows={2} value={notes} disabled={locked} onChange={e => setNotes(e.target.value)} /></div>
    {title.trim() && !validTitle ? <p className="error">Keep the title to {TITLE_MAX_LENGTH} characters or fewer.</p> : null}
    {resolvedElsewhere ? <p className="error" role="alert">This pending save was resolved elsewhere. Close this form and check your task list before creating it again.</p> : error ? <p className="error" role="alert">{error}</p> : null}
    <div className="form-actions">
      {resolvedElsewhere ? null : pending && !rejected ? <button type="button" disabled={busy} onClick={() => void check()}>{busy ? "Checking…" : "Check save status"}</button> : <button type="submit" disabled={busy || !validTitle}>{busy ? "Saving…" : "Add task"}</button>}
      <button type="button" className="link" disabled={busy || (!!pending && !rejected && !resolvedElsewhere)} onClick={() => void cancel()}>Cancel</button>
    </div>
  </form>;
}
