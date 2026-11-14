import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { Today } from "./Today";
import type { Planning, Project, Task } from "./api";

const stamp = "2026-11-11T12:00:00Z";
const project: Project = { id: "p", name: "Seminar", is_default: false, created_at: stamp, updated_at: stamp, revision: 1 };
const parent: Task = { id: "parent", project_id: "p", parent_id: null, title: "Discussion", notes: "", deadline: null, estimate_minutes: null, completed: false, completed_at: null, subtask_count: 2, completed_subtask_count: 1, created_at: stamp, updated_at: stamp, revision: 1 };
const child: Task = { ...parent, id: "child", parent_id: "parent", title: "Read source", subtask_count: 0, completed_subtask_count: 0 };
const done: Task = { ...child, id: "done", title: "Outline", completed: true, completed_at: stamp };
const plan: Planning = { today: "2026-11-11", timezone: "America/Los_Angeles", week_start: "2026-11-09", week_end: "2026-11-15", tasks: [parent, child, done], placements: [child, done].map((task) => ({ id: `placement-${task.id}`, task_id: task.id, planned_date: "2026-11-11", created_at: stamp, updated_at: stamp, revision: 1 })) };

function renderToday(onRun = vi.fn(async (work: () => Promise<unknown>) => { await work(); })) {
  const onTrack = vi.fn();
  render(<Today visible={false} lastSessionId={null} plan={plan} projects={[project]} loading={false} error={null} locked={false} onRun={onRun} onTrack={onTrack} onRetry={vi.fn()} />);
  return { onTrack };
}

test("shows service-today leaf work with project and parent, start and compact reopening", async () => {
  const user = userEvent.setup();
  const { onTrack } = renderToday();
  const section = screen.getByRole("region", { name: "Today" });
  expect(within(section).getByText("Seminar / Discussion")).toBeVisible();
  expect(within(section).getByText("1 unfinished · 1 complete")).toBeVisible();
  expect(within(section).queryByText("Outline")).not.toBeInTheDocument();
  await user.click(within(section).getByRole("button", { name: "Start Read source" }));
  expect(onTrack).toHaveBeenCalledWith("child");
  await user.click(within(section).getByRole("button", { name: "Completed · 1" }));
  const checkbox = within(section).getByRole("checkbox", { name: "Outline — Seminar / Discussion" });
  expect(checkbox).toBeChecked();
  expect(within(section).getByText("Outline")).toHaveClass("today-task-title");
});

test("failed completion keeps the task and offers an actionable error", async () => {
  const user = userEvent.setup();
  renderToday(vi.fn(async () => { throw new Error("network"); }));
  await user.click(screen.getByRole("checkbox", { name: "Read source — Seminar / Discussion" }));
  expect(screen.getByRole("checkbox", { name: "Read source — Seminar / Discussion" })).not.toBeChecked();
  expect(screen.getByRole("alert")).toHaveTextContent("Could not save this task");
});

test("planning errors can be retried from Today", async () => {
  const onRetry = vi.fn();
  render(<Today visible={false} lastSessionId={null} plan={plan} projects={[project]} loading={false} error="offline" locked onRun={vi.fn()} onTrack={vi.fn()} onRetry={onRetry} />);
  await userEvent.setup().click(screen.getByRole("button", { name: "Retry" }));
  expect(onRetry).toHaveBeenCalledOnce();
});

test("summarises planned time and shows start times, estimates and today's calendar events", () => {
  const timed = { ...child, estimate_minutes: 30 };
  const second = { ...child, id: "second", title: "Write notes", estimate_minutes: 50 };
  const event = { account_key: "a", calendar_id: "c", calendar_summary: "Personal", color: "", event_id: "e1", summary: "Gym", location: "", html_link: "", all_day: false, start_at: "2026-11-11T10:00:00", end_at: "2026-11-11T11:00:00", first_day: "2026-11-11", last_day: "2026-11-11", task_id: null };
  const other = { ...event, event_id: "e2", summary: "Tomorrow only", first_day: "2026-11-12", last_day: "2026-11-12" };
  const allDay = { ...event, event_id: "e3", summary: "Holiday", all_day: true, start_at: null, end_at: null };
  const timedPlan: Planning = { ...plan, tasks: [parent, timed, second], calendar_events: [event, other, allDay],
    placements: [{ ...plan.placements[0], start_time: "14:00" }, { ...plan.placements[0], id: "placement-second", task_id: "second" }] };
  render(<Today visible={false} lastSessionId={null} plan={timedPlan} projects={[project]} loading={false} error={null} locked={false} onRun={vi.fn()} onTrack={vi.fn()} onRetry={vi.fn()} />);
  expect(screen.getByText("2 unfinished · 0 complete · 1h 20m planned")).toBeVisible();
  expect(screen.getByText("14:00")).toBeVisible();
  expect(screen.getByText("30 min")).toBeVisible();
  const events = screen.getByRole("list", { name: "Calendar events today" });
  expect(within(events).getByText("Gym")).toBeVisible();
  expect(within(events).getByText("All day")).toBeVisible();
  expect(within(events).queryByText("Tomorrow only")).not.toBeInTheDocument();
});

test("keyboard shortcuts move, start and complete the focused task and open other views", async () => {
  const user = userEvent.setup();
  const onTrack = vi.fn(); const onAddTask = vi.fn(); const onShowWeek = vi.fn(); const onShowProjects = vi.fn();
  const onRun = vi.fn(async (work: () => Promise<unknown>) => { await work(); });
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
  const second = { ...child, id: "second", title: "Write notes" };
  const twoPlan: Planning = { ...plan, tasks: [parent, child, second], placements: [plan.placements[0], { ...plan.placements[0], id: "placement-second", task_id: "second" }] };
  render(<Today visible lastSessionId={null} plan={twoPlan} projects={[project]} loading={false} error={null} locked={false} onRun={onRun} onTrack={onTrack} onRetry={vi.fn()}
    onAddTask={onAddTask} onShowWeek={onShowWeek} onShowProjects={onShowProjects} />);
  const rows = () => screen.getAllByRole("listitem").filter((item) => item.classList.contains("today-task"));
  expect(rows()[0]).toHaveClass("today-task-focused");
  await user.keyboard("{ArrowDown}");
  expect(rows()[1]).toHaveClass("today-task-focused");
  await user.keyboard("{Enter}");
  expect(onTrack).toHaveBeenCalledWith("second");
  await user.keyboard("x");
  expect(onRun).toHaveBeenCalledWith(expect.any(Function), "Task marked complete.");
  await user.keyboard("nwp");
  expect(onAddTask).toHaveBeenCalledOnce();
  expect(onShowWeek).toHaveBeenCalledOnce();
  expect(onShowProjects).toHaveBeenCalledOnce();
});

test("shortcuts are ignored while typing or when Today is hidden", async () => {
  const user = userEvent.setup();
  const onShowWeek = vi.fn();
  const { rerender } = render(<><input aria-label="Notes" /><Today visible lastSessionId={null} plan={plan} projects={[project]} loading={false} error={null} locked={false} onRun={vi.fn()} onTrack={vi.fn()} onRetry={vi.fn()} onShowWeek={onShowWeek} /></>);
  await user.click(screen.getByRole("textbox", { name: "Notes" }));
  await user.keyboard("w");
  expect(onShowWeek).not.toHaveBeenCalled();
  rerender(<><input aria-label="Notes" /><Today visible={false} lastSessionId={null} plan={plan} projects={[project]} loading={false} error={null} locked={false} onRun={vi.fn()} onTrack={vi.fn()} onRetry={vi.fn()} onShowWeek={onShowWeek} /></>);
  (document.activeElement as HTMLElement).blur();
  await user.keyboard("w");
  expect(onShowWeek).not.toHaveBeenCalled();
});
