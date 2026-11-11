import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { prepareCapture, readPendingCapture, retryCapture } from "./taskCaptureRecovery";
import type { TaskCapture } from "./api";

const capture: TaskCapture = { operation_id: "one", project_id: "project", title: "Read", notes: "kept", deadline: null, estimate_minutes: 30, planned_date: "2026-11-12" };
const response = () => new Response(JSON.stringify({ task: { id: "task" }, placement: { id: "placement" } }), { status: 201 });
beforeEach(() => localStorage.clear());
afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

test("a lost response survives reload and retries the exact request", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new TypeError("response lost")).mockResolvedValueOnce(response());
  prepareCapture(capture);
  await expect(retryCapture()).rejects.toThrow();
  expect(readPendingCapture()).toEqual(capture);
  await expect(retryCapture()).resolves.toMatchObject({ task: { id: "task" } });
  expect(JSON.parse(String(fetcher.mock.calls[0][1]?.body))).toEqual(capture);
  expect(fetcher.mock.calls[1][1]?.body).toBe(fetcher.mock.calls[0][1]?.body);
  expect(readPendingCapture()).toBeNull();
});

test("pending or corrupted recovery data is never overwritten", () => {
  prepareCapture(capture);
  expect(() => prepareCapture({ ...capture, operation_id: "two" })).toThrow();
  localStorage.setItem("bearplans.task-capture.pending.v1", "broken");
  expect(() => readPendingCapture()).toThrow(/recovery data has been kept/);
  expect(() => prepareCapture(capture)).toThrow();
  expect(localStorage.getItem("bearplans.task-capture.pending.v1")).toBe("broken");
});

test("a malformed success and a rejected request retain the original recovery data", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("{}", { status: 201 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ error: { message: "Closed week" } }), { status: 409 }));
  prepareCapture(capture);
  await expect(retryCapture()).rejects.toThrow(/confirm/);
  await expect(retryCapture()).rejects.toThrow(/Closed week/);
  expect(readPendingCapture()).toEqual(capture);
});

test("storage failure prevents preparing a request", () => {
  const storage = { getItem: () => null, setItem: () => { throw new Error("unavailable"); } } as unknown as Storage;
  const fetcher = vi.spyOn(globalThis, "fetch");
  expect(() => prepareCapture(capture, storage)).toThrow("unavailable");
  expect(fetcher).not.toHaveBeenCalled();
});
