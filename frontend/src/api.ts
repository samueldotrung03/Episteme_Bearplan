// Typed client for the local BearPlans service. Paths are same-origin.

export const TITLE_MAX_LENGTH = 200;
export const NOTES_MAX_LENGTH = 2000;
export const NAME_MAX_LENGTH = 100;
export const ESTIMATE_MIN_MINUTES = 1;
export const ESTIMATE_MAX_MINUTES = 10080;

export interface Project {
  id: string;
  name: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  revision: number;
}

export interface Task {
  id: string;
  project_id: string;
  parent_id: string | null;
  title: string;
  notes: string;
  deadline: string | null;
  estimate_minutes: number | null;
  /** Derived for a task with subtasks: true only when every subtask is complete. */
  completed: boolean;
  completed_at: string | null;
  subtask_count: number;
  completed_subtask_count: number;
  created_at: string;
  updated_at: string;
  revision: number;
}

/** Fields a task edit may change. Omit one to leave it alone; null clears it. */
export interface TaskEdit {
  title?: string;
  notes?: string | null;
  deadline?: string | null;
  estimate_minutes?: number | null;
}

export interface NewTask extends TaskEdit {
  title: string;
  project_id?: string;
  parent_id?: string;
}

export class ApiError extends Error {
  readonly field?: string;
  readonly status?: number;
  readonly code?: string;

  constructor(message: string, field?: string, status?: number, code?: string) {
    super(message);
    this.field = field;
    this.status = status;
    this.code = code;
  }
}

export interface AssistantStatus {
  available: boolean; read_only: boolean; prompt_version: string;
  models: { name: string; digest: string; details: Record<string, unknown> }[];
}
export interface AssistantSource { tool: string; arguments: Record<string, unknown>; data: Record<string, unknown> }
/** A change the model prepared. Nothing is saved until the user applies it. */
export interface AssistantProposal {
  kind: string; arguments: Record<string, unknown>; summary: string; undoable: boolean;
  expected: { tasks: Record<string, number>; session_id: string | null; session_revision: number | null; preview_token?: string | null };
  preview: Record<string, unknown>;
}
/** The gate's questions when a change request lacks details; pending is returned on the next turn. */
export interface AssistantClarification {
  questions: string[]; choices: Record<string, { value: string; label: string }[]> | null; pending: Record<string, unknown>;
}
export interface AssistantReply {
  answer: string; sources: AssistantSource[]; proposals?: AssistantProposal[]; model: string; elapsed_seconds: number; read_only: boolean; rounds: number;
  kind?: "answer" | "proposal" | "clarify" | "blocked" | "unsupported" | "stopped";
  clarification?: AssistantClarification | null;
  route?: { intent: string; agents: string[] };
}
export interface AssistantTurn { pending?: Record<string, unknown> | null; choice?: { slot: string; value: string } | null }
export interface AssistantActionResult { operation_id: string; kind: string; summary: string; applied_at: string; undoable: boolean; replayed: boolean }
export interface AssistantUndoResult { operation_id: string; action_operation_id: string; undone_at: string; summary: string; replayed: boolean }
export function applyAssistantAction(proposal: AssistantProposal, operationId: string): Promise<AssistantActionResult> {
  return request<AssistantActionResult>("/api/assistant/actions/apply", json("POST", { proposal, operation_id: operationId }));
}
export function undoAssistantAction(operationId: string, undoOperationId: string): Promise<AssistantUndoResult> {
  return request<AssistantUndoResult>(`/api/assistant/actions/${encodeURIComponent(operationId)}/undo`, json("POST", { undo_operation_id: undoOperationId }));
}
export function getAssistantStatus(signal?: AbortSignal): Promise<AssistantStatus> {
  return request<AssistantStatus>("/api/assistant/status", { signal });
}
export function askAssistant(model: string, prompt: string, context: { project_id: string | null; date: string | null }, signal?: AbortSignal, turn: AssistantTurn = {}): Promise<AssistantReply> {
  const body = { model, prompt, context, ...(turn.pending ? { pending: turn.pending } : {}), ...(turn.choice ? { choice: turn.choice } : {}) };
  return request<AssistantReply>("/api/assistant/chat", { ...json("POST", body), signal });
}

export interface StatisticsState {
  today: string;
  timezone: string;
  completion: { completed: number; total: number; percent: number };
  active_microseconds: number;
  session_count: number;
  days: { date: string; active_microseconds: number; completed: number }[];
  projects: { project_id: string; name: string; completion: StatisticsState["completion"]; active_microseconds: number }[];
  tasks: { task_id: string; project_id: string; title: string; parent_title: string | null; current_leaf: boolean; completed: boolean | null;
    estimate_minutes: number | null; active_microseconds: number; session_count: number; missed_count?: number }[];
  missed?: number;
  weeks?: { week_start: string; week_end: string; completed: number; total: number; missed: number }[];
}

export function getStatistics(signal?: AbortSignal): Promise<StatisticsState> {
  return request<StatisticsState>("/api/statistics", { signal });
}

export interface IntervalEdit { id: string; active_microseconds: number }
export interface CorrectionDraft { expected_revision: number; reason: string; intervals: IntervalEdit[] }
export interface SavedSession {
  id: string; task_title: string; project_name: string; parent_title: string | null; finished_at: string;
  duration_minutes: number; active_microseconds: number; outcome: string; revision: number;
  blocked_reason: string | null; coin_contribution: number | null;
  intervals: (IntervalEdit & { started_at: string; ended_at: string | null; maximum_microseconds: number })[];
  history: { operation_id: string; reason: string; created_at: string; before: IntervalEdit[]; after: IntervalEdit[] }[];
}
export interface CorrectionPreview {
  session_id: string; preview_token: string; before_microseconds: number; after_microseconds: number;
  coin_delta: number; balance_before: number; balance_after: number; coin_contribution_after: number | null;
  tree_before: string | null; tree_after: string | null; timezone: string;
  days: { date: string; before_microseconds: number; after_microseconds: number;
    day_total_before_microseconds: number; day_total_after_microseconds: number; qualified_before: boolean; qualified_after: boolean }[];
}
export interface PendingCorrection { session_id: string; draft: CorrectionDraft; preview_token: string; operation_id: string }
export interface CorrectionResult { operation_id: string; session_id: string; revision: number; active_microseconds: number;
  coin_delta: number; balance_at_save: number; tree_outcome: string | null }
export async function getSavedSessions(signal?: AbortSignal): Promise<SavedSession[]> {
  return (await request<{ sessions: SavedSession[] }>("/api/sessions", { signal })).sessions;
}
export function previewCorrection(id: string, draft: CorrectionDraft): Promise<CorrectionPreview> {
  return request<CorrectionPreview>(`/api/sessions/${encodeURIComponent(id)}/correction/preview`, json("POST", draft));
}
export function applyCorrection(pending: PendingCorrection): Promise<CorrectionResult> {
  return request<CorrectionResult>(`/api/sessions/${encodeURIComponent(pending.session_id)}/correction`, json("POST", {
    ...pending.draft, preview_token: pending.preview_token, operation_id: pending.operation_id,
  }));
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}) },
    });
  } catch (error) {
    if (init?.signal?.aborted) throw error;
    throw new ApiError("Cannot reach the BearPlans service. Is it still running?");
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (body as { error?: { message?: unknown; field?: unknown; code?: unknown } } | null)?.error;
    const message = typeof error?.message === "string" ? error.message : `The service returned an error (${response.status}).`;
    throw new ApiError(message, typeof error?.field === "string" ? error.field : undefined,
      response.status, typeof error?.code === "string" ? error.code : undefined);
  }
  return body as T;
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export async function listProjects(signal?: AbortSignal): Promise<Project[]> {
  return (await request<{ projects: Project[] }>("/api/projects", { signal })).projects;
}

export function createProject(name: string): Promise<Project> {
  return request<Project>("/api/projects", json("POST", { name }));
}

export function renameProject(id: string, name: string): Promise<Project> {
  return request<Project>(`/api/projects/${encodeURIComponent(id)}`, json("PATCH", { name }));
}

export interface TaskList {
  tasks: Task[];
  progress: { completed: number; total: number };
}

export async function listTasks(projectId?: string, signal?: AbortSignal): Promise<TaskList> {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return request<TaskList>(`/api/tasks${query}`, { signal });
}

export function createTask(task: NewTask): Promise<Task> {
  return request<Task>("/api/tasks", json("POST", task));
}

export interface TaskCapture extends NewTask { operation_id: string; planned_date: string | null }
export interface TaskCaptureResult { task: Task; placement: Placement | null }

/** An unparseable success is uncertain: the service may already have committed. */
export async function captureTask(capture: TaskCapture): Promise<TaskCaptureResult> {
  const result = await request<TaskCaptureResult>("/api/task-captures", json("POST", capture));
  if (!result || typeof result !== "object" || !result.task || typeof result.task.id !== "string"
      || !(result.placement === null || (typeof result.placement === "object" && typeof result.placement.id === "string"))) {
    throw new ApiError("Could not confirm the saved task. Retry the same request.");
  }
  return result;
}

export function updateTask(id: string, edit: TaskEdit): Promise<Task> {
  return request<Task>(`/api/tasks/${encodeURIComponent(id)}`, json("PATCH", edit));
}

export function setTaskCompletion(id: string, complete: boolean): Promise<Task> {
  return request<Task>(`/api/tasks/${encodeURIComponent(id)}/completion`, json("PUT", { complete }));
}

export function removeSubtask(id: string): Promise<Task> {
  return request<Task>(`/api/tasks/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export interface Placement {
  id: string;
  task_id: string;
  planned_date: string;
  /** Optional local start time "HH:MM"; a timed task gets a Google Calendar event. */
  start_time?: string | null;
  created_at: string;
  updated_at: string;
  revision: number;
}

export interface Planning {
  today: string;
  timezone: string;
  week_start: string;
  week_end: string;
  tasks: Task[];
  /** Current open-week placements, including dates outside the displayed week. */
  placements: Placement[];
  closed_week?: ClosedWeek | null;
  closed_weeks?: ClosedWeekSummary[];
  /** Events from followed Google calendars in this week (read-only). */
  calendar_events?: GoogleEvent[];
  /** Unfinished leaf tasks whose latest plan is before today (B1; independent of the displayed week). */
  earlier_unfinished?: EarlierUnfinishedTask[];
}

export interface EarlierUnfinishedTask {
  id: string;
  title: string;
  project_id: string;
  project_name: string;
  parent_id: string | null;
  parent_title: string | null;
  /** YYYY-MM-DD, the latest saved placement before today. */
  last_planned_date: string;
  deadline: string | null;
  estimate_minutes: number | null;
}

export interface HistoricalTask extends Task {
  project_name: string;
  parent_title: string | null;
}

export interface ClosedWeek {
  snapshot_version: 1;
  week_start: string;
  week_end: string;
  closed_at: string | null;
  timezone: string;
  tasks: HistoricalTask[];
  placements: Placement[];
  completed: number;
  total: number;
}

export interface ClosedWeekSummary {
  week_start: string;
  week_end: string;
  closed_at: string;
  completed: number;
  total: number;
}

export interface ClosePreview { preview_token: string; snapshot: ClosedWeek }
export interface CarryoverCandidate {
  task_id: string;
  snapshot_task: HistoricalTask;
  task: Task | null;
  eligible: boolean;
  reason: string | null;
  existing_planned_date: string | null;
  suggested_date?: string | null;
  start_time?: string | null;
}
export interface CarryoverOptions {
  week_start: string;
  destination_start: string;
  destination_end: string;
  candidates: CarryoverCandidate[];
}
export interface CarryoverSelection { task_id: string; planned_date: string }
export interface CarryoverPreview {
  preview_token: string;
  week_start: string;
  destination_start: string;
  destination_end: string;
  items: (CarryoverSelection & { task: Task; project_name: string; parent_title: string | null; start_time?: string | null })[];
}

const weekPath = (week: string) => `/api/weeks/${encodeURIComponent(week)}`;
export function previewCloseWeek(week: string): Promise<ClosePreview> {
  return request<ClosePreview>(`${weekPath(week)}/close-preview`);
}
export function closeWeek(week: string, previewToken: string): Promise<ClosedWeek> {
  return request<ClosedWeek>(`${weekPath(week)}/close`, json("POST", { preview_token: previewToken }));
}
export function getCarryover(week: string): Promise<CarryoverOptions> {
  return request<CarryoverOptions>(`${weekPath(week)}/carryover`);
}
export function previewCarryover(week: string, selections: CarryoverSelection[]): Promise<CarryoverPreview> {
  return request<CarryoverPreview>(`${weekPath(week)}/carryover-preview`, json("POST", { selections }));
}
export function applyCarryover(week: string, operationId: string, previewToken: string, selections: CarryoverSelection[]): Promise<{ operation_id: string; week_start: string; placements: Placement[] }> {
  return request(`${weekPath(week)}/carryover`, json("POST", { operation_id: operationId, preview_token: previewToken, selections }));
}

export function getPlanning(week?: string, signal?: AbortSignal): Promise<Planning> {
  return request<Planning>(`/api/planning${week ? `?week=${encodeURIComponent(week)}` : ""}`, { signal });
}

export function assignTask(taskId: string, plannedDate: string): Promise<Placement> {
  return request<Placement>("/api/placements", json("POST", { task_id: taskId, planned_date: plannedDate }));
}

export function movePlacement(id: string, plannedDate: string): Promise<Placement> {
  return request<Placement>(`/api/placements/${encodeURIComponent(id)}`, json("PATCH", { planned_date: plannedDate }));
}

export function setPlacementTime(id: string, startTime: string | null): Promise<Placement> {
  return request<Placement>(`/api/placements/${encodeURIComponent(id)}/time`, json("PUT", { start_time: startTime }));
}

export function removePlacement(id: string): Promise<{ removed: string }> {
  return request<{ removed: string }>(`/api/placements/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export interface TimerRecovery {
  id: string;
  kind: "service_restart" | "sleep" | "clock_change" | "checkpoint_gap";
  reason: string;
  checkpoint_at: string;
  detected_at: string;
  confirmed_active_seconds: number;
  measured_sleep_seconds: number | null;
  resolved_at: string | null;
  resolution: "resume" | "finish" | null;
}

export type TreeSpecies = "pine" | "birch" | "oak" | "cherry";

export interface ShopSpecies {
  id: TreeSpecies;
  name: string;
  price: number;
  owned: boolean;
}

export interface CoinEntry {
  id: string;
  kind: "session_award" | "purchase" | "session_adjustment";
  amount: number;
  session_id: string | null;
  species: TreeSpecies | null;
  created_at: string;
}

export interface ShopState {
  balance: number;
  coins_per_minute: number;
  species: ShopSpecies[];
  recent_entries: CoinEntry[];
}

export function getShop(signal?: AbortSignal): Promise<ShopState> {
  return request<ShopState>("/api/shop", { signal });
}

export interface StreakDay {
  date: string;
  active_microseconds: number;
  qualified: boolean;
}

export interface StreakState {
  today: string;
  timezone: string;
  threshold_microseconds: number;
  current_streak: number;
  streak_through: string | null;
  days: StreakDay[];
}

export function getStreaks(signal?: AbortSignal): Promise<StreakState> {
  return request<StreakState>("/api/streaks", { signal });
}

export function purchaseSpecies(species: TreeSpecies, expectedPrice: number, operationId: string): Promise<{ operation_id: string; species: TreeSpecies; price: number; balance: number }> {
  return request("/api/shop/purchases", json("POST", { species, expected_price: expectedPrice, operation_id: operationId }));
}

export interface TreeProgress {
  id: string;
  species: TreeSpecies;
  stage: "seedling" | "sapling" | "mature";
  progress: number;
  outcome: "mature" | "unfinished" | null;
}

export interface ForestTree extends TreeProgress {
  session_id: string;
  task_title: string;
  project_name: string;
  parent_title: string | null;
  started_at: string;
  finished_at: string;
  duration_minutes: number;
  active_seconds: number;
}

export async function getForest(signal?: AbortSignal): Promise<ForestTree[]> {
  return (await request<{ trees: ForestTree[] }>("/api/forest", { signal })).trees;
}

export interface TimerSession {
  id: string;
  start_operation_id: string;
  task_id: string;
  task_title: string;
  project_id: string;
  project_name: string;
  parent_title: string | null;
  state: "running" | "paused" | "needs_review" | "finished";
  duration_minutes: number;
  requested_seconds: number;
  active_seconds: number;
  remaining_seconds: number;
  started_at: string;
  checkpoint_at: string;
  deadline_at: string | null;
  finished_at: string | null;
  outcome: "completed" | "finished_early" | "interrupted" | null;
  review_reason: string | null;
  recovery?: TimerRecovery | null;
  tree: TreeProgress | null;
  coin_award: number | null;
  revision: number;
}

export interface TimerState {
  server_now: string;
  active_session: TimerSession | null;
  last_session: TimerSession | null;
}

export interface TimerControl {
  operation_id: string;
  expected_revision: number;
  discard_uncertain?: boolean;
}

export function getTimer(signal?: AbortSignal): Promise<TimerState> {
  return request<TimerState>("/api/timer", { signal });
}

export function startTimer(operationId: string, taskId: string, durationMinutes: number, species: TreeSpecies = "pine"): Promise<TimerState> {
  // Pine is also the service default. Omitting it keeps tracking available when
  // the browser has updated but the local service has not restarted yet.
  return request<TimerState>("/api/timer/start", json("POST", { operation_id: operationId, task_id: taskId, duration_minutes: durationMinutes,
    ...(species === "pine" ? {} : { species }) }));
}

export function controlTimer(id: string, action: "pause" | "resume" | "finish", control: TimerControl): Promise<TimerState> {
  return request<TimerState>(`/api/timer/${encodeURIComponent(id)}/${action}`, json("POST", control));
}

export function recoverTimer(id: string, resolution: "resume" | "finish", control: TimerControl): Promise<TimerState> {
  return request<TimerState>(`/api/timer/${encodeURIComponent(id)}/recover`, json("POST", { ...control, resolution, discard_uncertain: true }));
}

export interface BCoursesCourse {
  course_id: string;
  name: string;
  course_code: string;
  term: string;
  followed: boolean;
  in_source: boolean;
  project_id: string | null;
}

export interface BCoursesAssignment {
  assignment_id: string;
  course_id: string;
  course_name: string;
  title: string;
  /** UTC instant from bCourses, or null when no due date is published. */
  due_at: string | null;
  /** The due date's day in BearPlans' calendar (what a task deadline gets). */
  due_date: string | null;
  html_url: string;
  points_possible: number | null;
  in_source: boolean;
  status: "new" | "added" | "dismissed";
  task_id: string | null;
  due_changed: boolean;
  accepted_due_date: string | null;
}

interface ProviderSyncEvidence {
  last_attempt_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
}

type GoogleSetup = "missing" | "unusable" | "configured";

interface CredentialStatus {
  set: boolean;
  saved_at: string | null;
  checked_at: string | null;
  check_ok: boolean | null;
  check_message: string | null;
}

export interface ConnectionsState {
  folder: string;
  bcourses: CredentialStatus;
  google: CredentialStatus & { setup: GoogleSetup; connected: boolean; revoked: boolean | null };
}

export function getConnections(signal?: AbortSignal): Promise<ConnectionsState> {
  return request("/api/connections", { signal });
}

export function saveBCoursesToken(token: string): Promise<ConnectionsState> {
  return request("/api/connections/bcourses", json("PUT", { token }));
}

export function checkBCoursesToken(): Promise<ConnectionsState> {
  return request("/api/connections/bcourses/check", { method: "POST" });
}

export function removeBCoursesToken(): Promise<ConnectionsState> {
  return request("/api/connections/bcourses", { method: "DELETE" });
}

export function saveGoogleClient(clientFile: string): Promise<ConnectionsState> {
  return request("/api/connections/google", json("PUT", { client_file: clientFile }));
}

export interface BCoursesState {
  configured: boolean;
  sync: ProviderSyncEvidence;
  courses: BCoursesCourse[];
  assignments: BCoursesAssignment[];
}

export function getBCourses(signal?: AbortSignal): Promise<BCoursesState> {
  return request("/api/bcourses", { signal });
}
export function refreshBCourses(): Promise<BCoursesState> {
  return request("/api/bcourses/refresh", { method: "POST" });
}
export function followBCourses(courseIds: string[]): Promise<BCoursesState> {
  return request("/api/bcourses/courses", json("PUT", { course_ids: courseIds }));
}
export function addBCoursesAssignment(id: string): Promise<{ assignment: BCoursesAssignment; task: Task; project_created: boolean }> {
  return request(`/api/bcourses/assignments/${encodeURIComponent(id)}/add`, { method: "POST" });
}
export function dismissBCoursesAssignment(id: string, dismissed: boolean): Promise<BCoursesAssignment> {
  return request(`/api/bcourses/assignments/${encodeURIComponent(id)}/dismissed`, json("PUT", { dismissed }));
}
export function resolveBCoursesDueDate(id: string, useNew: boolean): Promise<BCoursesAssignment> {
  return request(`/api/bcourses/assignments/${encodeURIComponent(id)}/due-date`, json("POST", { use_new: useNew }));
}

interface GoogleSyncStatus extends ProviderSyncEvidence {
  paused_at: string | null;
  syncing: boolean;
  account_status: "unverified" | "verified" | "different_account" | "unowned_links";
  account_review_key: string | null;
  other_account: boolean;
  pending_create_unverified?: boolean;
  pending_create?: { kind: "task_list" | "task" | "calendar" | "event"; review_key: string; context: string } | null;
  synced_lists: number;
  synced_tasks: number;
  synced_events: number;
}

export interface GoogleState {
  setup: GoogleSetup;
  activity: "idle" | "syncing" | "refreshing_calendars";
  connection_changing: boolean;
  pausing: boolean;
  configured: boolean;
  /** A matching grant is saved locally. This does not establish live access. */
  connected: boolean;
  sign_in_pending: boolean;
  sign_in_attempt_id: string | null;
  sign_in_error: string | null;
  missing_permissions: string[];
  tasks: GoogleSyncStatus;
  status: "not_set_up" | "signed_out" | "signing_in" | "needs_attention" | "pausing" | "paused" | "syncing" | "not_synced" | "working";
  /** Only meaningful on a response to Disconnect. */
  revoked: boolean | null;
}

export function getGoogle(signal?: AbortSignal): Promise<GoogleState> {
  return request("/api/google", { signal });
}
export function connectGoogle(): Promise<{ url: string; attempt_id: string }> {
  return request("/api/google/connect", { method: "POST" });
}
export function cancelGoogleSignIn(attemptId: string): Promise<{ cancelled: boolean }> {
  return request("/api/google/cancel-sign-in", json("POST", { attempt_id: attemptId }));
}

export function disconnectGoogle(): Promise<GoogleState> {
  return request("/api/google/disconnect", { method: "POST" });
}
export function useGoogleAccount(reviewKey: string): Promise<GoogleState> {
  return request("/api/google/use-this-account", json("POST", { review_key: reviewKey }));
}
export function verifyGoogleCreate(): Promise<GoogleState> {
  return request("/api/google/verify-pending-create", { method: "POST" });
}
export function resolveGoogleCreate(reviewKey: string): Promise<GoogleState> {
  return request("/api/google/resolve-uncertain-create", json("POST", { review_key: reviewKey, accept_possible_duplicate: true }));
}
export function setGoogleSyncPaused(paused: boolean): Promise<GoogleState> {
  return request(paused ? "/api/google/pause" : "/api/google/resume", { method: "POST" });
}
export function syncGoogleTasks(): Promise<GoogleState> {
  return request("/api/google/tasks/sync", { method: "POST" });
}

export interface GoogleCalendar {
  account_key: string;
  calendar_id: string;
  summary: string;
  color: string;
  is_primary: boolean;
  followed: boolean;
}

export interface GoogleEvent {
  account_key: string;
  calendar_id: string;
  calendar_summary: string;
  color: string;
  event_id: string;
  summary: string;
  location: string;
  html_link: string;
  all_day: boolean;
  start_at: string | null;
  end_at: string | null;
  first_day: string;
  last_day: string;
  /** The BearPlans task made from this event, if any. */
  task_id: string | null;
}

export function getGoogleCalendars(signal?: AbortSignal): Promise<GoogleCalendar[]> {
  return request("/api/google/calendars", { signal });
}
export function refreshGoogleCalendars(options?: { automatic: true; signal: AbortSignal }): Promise<GoogleCalendar[]> {
  const path = options ? "/api/google/calendars/refresh?automatic=true" : "/api/google/calendars/refresh";
  return request(path, { method: "POST", signal: options?.signal });
}
export function followGoogleCalendars(accountKey: string, calendarIds: string[]): Promise<GoogleCalendar[]> {
  return request("/api/google/calendars", json("PUT", { account_key: accountKey, calendar_ids: calendarIds }));
}
export function getGoogleEvents(start: string, end: string, signal?: AbortSignal): Promise<GoogleEvent[]> {
  return request(`/api/google/events?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`, { signal });
}
export function addGoogleEvent(accountKey: string, calendarId: string, eventId: string): Promise<{ event: GoogleEvent; task: Task; planned: boolean }> {
  return request("/api/google/events/add", json("POST", { account_key: accountKey, calendar_id: calendarId, event_id: eventId }));
}
export function getGoogleChanges(signal?: AbortSignal): Promise<{ version: number }> {
  return request("/api/google/changes", { signal });
}
