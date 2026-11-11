import { ApiError, captureTask, type TaskCapture, type TaskCaptureResult } from "./api";

const PENDING_KEY = "bearplans.task-capture.pending.v1";
const LOCK_NAME = "bearplans.task-capture.v1";
export class CaptureRecoveryError extends Error {}

export function readPendingCapture(storage: Storage = localStorage): TaskCapture | null {
  const raw = storage.getItem(PENDING_KEY);
  if (raw === null) return null;
  try {
    const value: unknown = JSON.parse(raw);
    if (value && typeof value === "object" && "operation_id" in value
      && typeof value.operation_id === "string" && value.operation_id.length > 0
      && "project_id" in value && typeof value.project_id === "string"
      && "title" in value && typeof value.title === "string"
      && "planned_date" in value && (value.planned_date === null || typeof value.planned_date === "string")) {
      return value as TaskCapture;
    }
  } catch { /* Preserve unreadable data rather than replacing an uncertain save. */ }
  throw new CaptureRecoveryError("A pending task save could not be read. Its recovery data has been kept.");
}

/** Fail closed when cross-window serialization isn't available. */
async function locked<T>(work: () => Promise<T>): Promise<T> {
  if (!navigator.locks?.request) throw new CaptureRecoveryError("This browser cannot safely coordinate task saves between windows. No task was sent.");
  return navigator.locks.request(LOCK_NAME, work);
}

function prepareCapture(capture: TaskCapture, storage: Storage): void {
  let existing: string | null;
  try { existing = storage.getItem(PENDING_KEY); }
  catch { throw new CaptureRecoveryError("Task save recovery storage is unavailable. No task was sent. Check your browser storage settings and try again."); }
  if (existing !== null) throw new CaptureRecoveryError("Resolve the pending task save before starting another.");
  try { storage.setItem(PENDING_KEY, JSON.stringify(capture)); }
  catch { throw new CaptureRecoveryError("Task save recovery storage is unavailable. No task was sent. Check your browser storage settings and try again."); }
}

async function attempt(storage: Storage): Promise<TaskCaptureResult> {
  const pending = readPendingCapture(storage);
  if (!pending) throw new CaptureRecoveryError("There is no pending task save to retry.");
  const result = await captureTask(pending);
  if (JSON.stringify(readPendingCapture(storage)) !== JSON.stringify(pending)) {
    throw new CaptureRecoveryError("The recovery record changed while saving. Check your task list before retrying.");
  }
  storage.removeItem(PENDING_KEY);
  return result;
}

/** Persist and send as one serialized operation, shared by all same-origin windows. */
export function startCapture(capture: TaskCapture, storage?: Storage): Promise<TaskCaptureResult> {
  return locked(async () => {
    let recoveryStorage: Storage;
    try { recoveryStorage = storage ?? localStorage; }
    catch { throw new CaptureRecoveryError("Task save recovery storage is unavailable. No task was sent. Check your browser storage settings and try again."); }
    prepareCapture(capture, recoveryStorage);
    return attempt(recoveryStorage);
  });
}

export function retryCapture(expectedOperationId: string, storage: Storage = localStorage): Promise<TaskCaptureResult> {
  return locked(() => {
    const pending = readPendingCapture(storage);
    if (!pending || pending.operation_id !== expectedOperationId) throw new CaptureRecoveryError("The pending task save changed in another window. Review it before continuing.");
    return attempt(storage);
  });
}

/** Only these structured responses prove this exact request was rejected without a write.
 * A replay checks its durable receipt before checking the closed week. An operation-ID
 * conflict, unknown response or storage failure must never authorize replacement. */
function definitiveRejection(error: unknown): error is ApiError {
  return error instanceof ApiError && ((error.status === 422 && error.code === "invalid_input")
    || (error.status === 409 && error.code === "week_conflict" && error.field === "planned_date"));
}

export type CaptureResolution = { saved: TaskCaptureResult } | { rejected: TaskCapture; error: ApiError };

/** Recheck before allowing editing/cancellation. A rejected draft stays durable. */
export function checkCapture(expectedOperationId: string, storage: Storage = localStorage): Promise<CaptureResolution> {
  return locked(async () => {
    const pending = readPendingCapture(storage);
    if (!pending) throw new CaptureRecoveryError("There is no pending task save to check.");
    if (pending.operation_id !== expectedOperationId) throw new CaptureRecoveryError("The pending task save changed in another window. Review it before continuing.");
    try { return { saved: await attempt(storage) }; }
    catch (error) {
      if (definitiveRejection(error)) return { rejected: pending, error };
      throw error;
    }
  });
}

/** Revalidate rejection under the same lock before replacing or discarding it. */
export function resolveRejectedCapture(expectedOperationId: string, replacement: TaskCapture | null, storage: Storage = localStorage): Promise<CaptureResolution> {
  return locked(async () => {
    const pending = readPendingCapture(storage);
    if (!pending) throw new CaptureRecoveryError("There is no pending task save to resolve.");
    if (pending.operation_id !== expectedOperationId) throw new CaptureRecoveryError("The pending task save changed in another window. Review it before continuing.");
    try { return { saved: await attempt(storage) }; }
    catch (error) {
      if (!definitiveRejection(error)) throw error;
      if (replacement) {
        if (replacement.operation_id === pending.operation_id) throw new CaptureRecoveryError("Use a new operation ID for changed task details.");
        storage.setItem(PENDING_KEY, JSON.stringify(replacement));
      } else storage.removeItem(PENDING_KEY);
      return { rejected: pending, error };
    }
  });
}
