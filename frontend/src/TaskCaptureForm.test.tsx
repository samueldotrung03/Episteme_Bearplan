import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, test, vi, expect } from "vitest";
import { TaskCaptureForm } from "./TaskCaptureForm";

const projectId = "project";
const ok = () => new Response(JSON.stringify({ task: { id: "task" }, placement: null }), { status: 201 });
const closed = () => new Response(JSON.stringify({ error: { code: "week_conflict", field: "planned_date", message: "That week is closed." } }), { status: 409 });
beforeEach(() => {
  localStorage.clear();
  Object.defineProperty(navigator, "locks", { configurable: true, value: { request: (_name: string, work: () => Promise<unknown>) => work() } });
});

test("saves task details and planned day in one request", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(async () => ok());
  const saved = vi.fn(); const user = userEvent.setup();
  render(<TaskCaptureForm projectId={projectId} onCancel={vi.fn()} onSaved={saved} />);
  await user.type(screen.getByLabelText("Title"), "Read paper");
  await user.type(screen.getByLabelText("Deadline"), "2026-11-20");
  await user.type(screen.getByLabelText("Planned day"), "2026-11-18");
  await user.type(screen.getByLabelText("Estimate (minutes)"), "30");
  await user.click(screen.getByRole("button", { name: "Add task" }));
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  expect(fetcher).toHaveBeenCalledOnce();
  expect(JSON.parse(String(fetcher.mock.calls[0][1]?.body))).toMatchObject({ title: "Read paper", project_id: projectId, deadline: "2026-11-20", planned_date: "2026-11-18", estimate_minutes: 30, operation_id: expect.any(String) });
});

test("lost response survives remount and checking replays the exact request", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new TypeError("offline")).mockImplementationOnce(async () => ok());
  const saved = vi.fn(); const user = userEvent.setup();
  const view = render(<TaskCaptureForm projectId={projectId} onCancel={vi.fn()} onSaved={saved} />);
  await user.type(screen.getByLabelText("Title"), "Read paper");
  await user.click(screen.getByRole("button", { name: "Add task" }));
  expect(await screen.findByRole("button", { name: "Check save status" })).toBeEnabled();
  await waitFor(() => expect(screen.getByRole("button", { name: "Check save status" })).toHaveFocus());
  expect(screen.getByLabelText("Title")).toBeDisabled();
  view.unmount();
  render(<TaskCaptureForm projectId={projectId} onCancel={vi.fn()} onSaved={saved} />);
  expect(screen.getByLabelText("Title")).toHaveValue("Read paper");
  await user.click(screen.getByRole("button", { name: "Check save status" }));
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  expect(fetcher.mock.calls[1][1]?.body).toBe(fetcher.mock.calls[0][1]?.body);
});

test("closed week keeps the draft, permits correction after checking and saves a new request", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementationOnce(async () => closed()).mockImplementationOnce(async () => closed()).mockImplementationOnce(async () => closed()).mockImplementationOnce(async () => ok());
  const saved = vi.fn(); const user = userEvent.setup();
  render(<TaskCaptureForm projectId={projectId} onCancel={vi.fn()} onSaved={saved} />);
  await user.type(screen.getByLabelText("Title"), "Read paper");
  await user.type(screen.getByLabelText("Planned day"), "2026-11-18");
  await user.click(screen.getByRole("button", { name: "Add task" }));
  await user.click(await screen.findByRole("button", { name: "Check save status" }));
  expect(await screen.findByText(/Your details are kept/)).toBeVisible();
  await waitFor(() => expect(screen.getByLabelText("Title")).toHaveFocus());
  await user.clear(screen.getByLabelText("Planned day"));
  await user.type(screen.getByLabelText("Planned day"), "2026-11-25");
  await user.click(screen.getByRole("button", { name: "Add task" }));
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  const first = JSON.parse(String(fetcher.mock.calls[0][1]?.body));
  const last = JSON.parse(String(fetcher.mock.calls[3][1]?.body));
  expect(last.planned_date).toBe("2026-11-25");
  expect(last.operation_id).not.toBe(first.operation_id);
});

test("unavailable recovery storage keeps the draft and sends no task", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch");
  const storage = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new DOMException("Storage unavailable", "SecurityError"); });
  const user = userEvent.setup();
  render(<TaskCaptureForm projectId={projectId} onCancel={vi.fn()} onSaved={vi.fn()} />);
  await user.type(screen.getByLabelText("Title"), "Keep this draft");
  await user.click(screen.getByRole("button", { name: "Add task" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/storage is unavailable.*no task was sent/i);
  expect(screen.getByLabelText("Title")).toHaveValue("Keep this draft");
  expect(screen.getByLabelText("Title")).toBeEnabled();
  expect(fetcher).not.toHaveBeenCalled();
  storage.mockRestore();
});

test("unavailable browser locks keep the draft and send no task", async () => {
  Object.defineProperty(navigator, "locks", { configurable: true, value: undefined });
  const fetcher = vi.spyOn(globalThis, "fetch");
  const user = userEvent.setup();
  render(<TaskCaptureForm projectId={projectId} onCancel={vi.fn()} onSaved={vi.fn()} />);
  await user.type(screen.getByLabelText("Title"), "Keep this draft");
  await user.click(screen.getByRole("button", { name: "Add task" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/cannot safely coordinate/i);
  expect(screen.getByLabelText("Title")).toHaveValue("Keep this draft");
  expect(screen.getByLabelText("Title")).toBeEnabled();
  expect(fetcher).not.toHaveBeenCalled();
});

test("denied access to browser storage keeps the draft and sends no task", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch");
  const user = userEvent.setup();
  render(<TaskCaptureForm projectId={projectId} onCancel={vi.fn()} onSaved={vi.fn()} />);
  await user.type(screen.getByLabelText("Title"), "Keep this draft");
  const storage = vi.spyOn(window, "localStorage", "get").mockImplementation(() => { throw new DOMException("Access denied", "SecurityError"); });
  try {
    await user.click(screen.getByRole("button", { name: "Add task" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/storage is unavailable.*no task was sent/i);
    expect(screen.getByLabelText("Title")).toHaveValue("Keep this draft");
    expect(screen.getByLabelText("Title")).toBeEnabled();
    expect(fetcher).not.toHaveBeenCalled();
  } finally { storage.mockRestore(); }
});

test("title length error is associated with the field and clears on correction", () => {
  render(<TaskCaptureForm projectId={projectId} onCancel={vi.fn()} onSaved={vi.fn()} />);
  const title = screen.getByLabelText("Title");
  fireEvent.change(title, { target: { value: "x".repeat(201) } });
  expect(title).toHaveAttribute("aria-invalid", "true");
  expect(title).toHaveAccessibleDescription("Keep the title to 200 characters or fewer.");
  expect(screen.getByRole("button", { name: "Add task" })).toBeDisabled();
  fireEvent.change(title, { target: { value: "Corrected title" } });
  expect(title).not.toHaveAttribute("aria-invalid");
  expect(title).not.toHaveAttribute("aria-describedby");
  expect(screen.getByRole("button", { name: "Add task" })).toBeEnabled();
});

test("a save resolved elsewhere does not steal focus from another control", async () => {
  localStorage.setItem("bearplans.task-capture.pending.v1", JSON.stringify({ operation_id: "pending", project_id: projectId, title: "Pending", planned_date: null, notes: null, deadline: null, estimate_minutes: null }));
  render(<><button type="button">Other work</button><TaskCaptureForm projectId={projectId} onCancel={vi.fn()} onSaved={vi.fn()} /></>);
  const other = screen.getByRole("button", { name: "Other work" });
  other.focus();
  localStorage.removeItem("bearplans.task-capture.pending.v1");
  fireEvent(window, new Event("storage"));
  expect(await screen.findByText(/resolved elsewhere/)).toBeVisible();
  expect(other).toHaveFocus();
});
