import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { startCapture, readPendingCapture, retryCapture, checkCapture, resolveRejectedCapture } from "./taskCaptureRecovery";
import type { TaskCapture } from "./api";

const capture: TaskCapture = { operation_id: "one", project_id: "project", title: "Read", notes: "kept", deadline: null, estimate_minutes: 30, planned_date: "2026-11-12" };
const response = () => new Response(JSON.stringify({ task: { id: "task" }, placement: { id: "placement" } }), { status: 201 });
beforeEach(() => {
  localStorage.clear();
  let queue = Promise.resolve();
  Object.defineProperty(navigator, "locks", { configurable: true, value: { request: (_name: string, work: () => Promise<unknown>) => {
    const next = queue.then(work); queue = next.then(() => undefined, () => undefined); return next;
  } } });
});
afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

test("a lost response survives reload and retries the exact request", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new TypeError("response lost")).mockResolvedValueOnce(response());
  await expect(startCapture(capture)).rejects.toThrow();
  expect(readPendingCapture()).toEqual(capture);
  await expect(retryCapture()).resolves.toMatchObject({ task: { id: "task" } });
  expect(JSON.parse(String(fetcher.mock.calls[0][1]?.body))).toEqual(capture);
  expect(fetcher.mock.calls[1][1]?.body).toBe(fetcher.mock.calls[0][1]?.body);
  expect(readPendingCapture()).toBeNull();
});

test("pending or corrupted recovery data is never overwritten", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("offline"));
  await expect(startCapture(capture)).rejects.toThrow();
  await expect(startCapture({ ...capture, operation_id: "two" })).rejects.toThrow();
  localStorage.setItem("bearplans.task-capture.pending.v1", "broken");
  expect(() => readPendingCapture()).toThrow(/recovery data has been kept/);
  await expect(startCapture(capture)).rejects.toThrow();
  expect(localStorage.getItem("bearplans.task-capture.pending.v1")).toBe("broken");
});

test("a malformed success and a rejected request retain the original recovery data", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("{}", { status: 201 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ error: { message: "Closed week" } }), { status: 409 }));
  await expect(startCapture(capture)).rejects.toThrow(/confirm/);
  await expect(retryCapture()).rejects.toThrow(/Closed week/);
  expect(readPendingCapture()).toEqual(capture);
});

test("storage failure prevents preparing a request", async () => {
  const storage = { getItem: () => null, setItem: () => { throw new Error("unavailable"); } } as unknown as Storage;
  const fetcher = vi.spyOn(globalThis, "fetch");
  await expect(startCapture(capture, storage)).rejects.toThrow("unavailable");
  expect(fetcher).not.toHaveBeenCalled();
});


test("serialized windows cannot overwrite an uncertain request", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("offline"));
  const results = await Promise.allSettled([startCapture(capture), startCapture({ ...capture, operation_id: "two" })]);
  expect(results.map((result) => result.status)).toEqual(["rejected", "rejected"]);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(readPendingCapture()).toEqual(capture);
});

test("closed-week rejection keeps the draft and permits a rechecked replacement", async () => {
  const closed = () => new Response(JSON.stringify({ error: { code: "week_conflict", field: "planned_date", message: "Closed week" } }), { status: 409 });
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => closed());
  await expect(startCapture(capture)).rejects.toThrow(/Closed week/);
  expect(await checkCapture()).toMatchObject({ rejected: capture });
  expect(readPendingCapture()).toEqual(capture);
  const revised = { ...capture, operation_id: "two", planned_date: "2026-11-19" };
  expect(await resolveRejectedCapture(revised)).toMatchObject({ rejected: capture });
  expect(readPendingCapture()).toEqual(revised);
});

test("an operation conflict or uncertain outcome never permits discard", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new TypeError("lost"))
    .mockResolvedValueOnce(new Response(JSON.stringify({ error: { code: "week_conflict", field: "operation_id", message: "Conflict" } }), { status: 409 }))
    .mockRejectedValueOnce(new TypeError("lost again"));
  await expect(startCapture(capture)).rejects.toThrow();
  await expect(resolveRejectedCapture(null)).rejects.toThrow(/Conflict/);
  await expect(resolveRejectedCapture(null)).rejects.toThrow();
  expect(readPendingCapture()).toEqual(capture);
});

test("a saved replay wins over a proposed cancellation", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new TypeError("lost")).mockResolvedValueOnce(response());
  await expect(startCapture(capture)).rejects.toThrow();
  expect(await resolveRejectedCapture(null)).toMatchObject({ saved: { task: { id: "task" } } });
  expect(readPendingCapture()).toBeNull();
});

test("missing cross-window locks prevents any request", async () => {
  Object.defineProperty(navigator, "locks", { configurable: true, value: undefined });
  const fetcher = vi.spyOn(globalThis, "fetch");
  await expect(startCapture(capture)).rejects.toThrow(/coordinate/);
  expect(fetcher).not.toHaveBeenCalled();
  expect(readPendingCapture()).toBeNull();
});
