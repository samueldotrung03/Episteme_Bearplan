import { captureTask, type TaskCapture, type TaskCaptureResult } from "./api";

// Persist before sending so a lost response or app restart can replay the same request.
const PENDING_KEY = "bearplans.task-capture.pending.v1";

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
  } catch { /* Preserve unreadable data rather than silently replacing an uncertain save. */ }
  throw new CaptureRecoveryError("A pending task save could not be read. Its recovery data has been kept.");
}

/** Do not send if storage is unavailable or another request needs recovery. */
export function prepareCapture(capture: TaskCapture, storage: Storage = localStorage): void {
  if (storage.getItem(PENDING_KEY) !== null) throw new CaptureRecoveryError("Resolve the pending task save before starting another.");
  storage.setItem(PENDING_KEY, JSON.stringify(capture));
}

/** Acknowledgement clears only this exact request; errors leave it available for replay. */
export async function retryCapture(storage: Storage = localStorage): Promise<TaskCaptureResult> {
  const pending = readPendingCapture(storage);
  if (!pending) throw new CaptureRecoveryError("There is no pending task save to retry.");
  const result = await captureTask(pending);
  const current = readPendingCapture(storage);
  if (current && JSON.stringify(current) === JSON.stringify(pending)) storage.removeItem(PENDING_KEY);
  return result;
}
