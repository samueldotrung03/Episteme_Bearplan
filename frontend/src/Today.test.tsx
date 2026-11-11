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
  render(<Today plan={plan} projects={[project]} loading={false} error={null} locked={false} onRun={onRun} onTrack={onTrack} />);
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
