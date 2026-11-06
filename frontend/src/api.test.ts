import { vi } from "vitest";
import { getConnections, getStreaks, startTimer, syncGoogleTasks, type ConnectionsState } from "./api";

const operationId = "00000000-0000-4000-8000-000000000001";
const taskId = "00000000-0000-4000-8000-000000000002";
const state = { server_now: "2026-10-20T16:00:00.000000Z", active_session: null, last_session: null };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

test("default and explicitly selected Pine remain compatible with the previous strict Start API", async () => {
  const bodies: Record<string, unknown>[] = [];
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
    bodies.push(body);
    return Object.keys(body).some((key) => !["operation_id", "task_id", "duration_minutes"].includes(key))
      ? json({ error: { message: "Extra inputs are not permitted." } }, 422) : json(state);
  });
  await expect(startTimer(operationId, taskId, 25)).resolves.toEqual(state);
  await expect(startTimer(operationId, taskId, 25, "pine")).resolves.toEqual(state);
  expect(bodies).toEqual([
    { operation_id: operationId, task_id: taskId, duration_minutes: 25 },
    { operation_id: operationId, task_id: taskId, duration_minutes: 25 },
  ]);
  expect(fetcher.mock.calls.every(([path]) => path === "/api/timer/start")).toBe(true);
});

test.each(["birch", "oak", "cherry"] as const)("new countdowns explicitly send the selected %s species", async (species) => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(state));
  await startTimer(operationId, taskId, 25, species);
  expect(JSON.parse(String(fetcher.mock.calls[0][1]?.body))).toEqual({ operation_id: operationId, task_id: taskId, duration_minutes: 25, species });
});

test("daily streak reads preserve service dates and use an abortable same-origin request", async () => {
  const controller = new AbortController();
  const streak = { today: "2026-10-21", timezone: "Pacific/Auckland", threshold_microseconds: 3_600_000_000, current_streak: 1, streak_through: "2026-10-21", days: [{ date: "2026-10-21", active_microseconds: 3_600_000_000, qualified: true }] };
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(streak));
  await expect(getStreaks(controller.signal)).resolves.toEqual(streak);
  expect(fetcher).toHaveBeenCalledWith("/api/streaks", { signal: controller.signal, headers: { Accept: "application/json" } });
});


test("connection setup reads use the local API and retain credential evidence independently", async () => {
  const controller = new AbortController();
  const empty = { set: false, saved_at: null, checked_at: null, check_ok: null, check_message: null };
  const setup: ConnectionsState = {
    folder: "~/fixture",
    bcourses: { ...empty, set: true, check_ok: false, checked_at: "2026-11-06T15:30:00Z", check_message: "Token rejected." },
    google: { ...empty, set: true, setup: "configured", connected: false, revoked: null },
  };
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(setup));
  await expect(getConnections(controller.signal)).resolves.toEqual(setup);
  expect(fetch).toHaveBeenCalledWith("/api/connections", { signal: controller.signal, headers: { Accept: "application/json" } });
});

test("the local API client retains the structured error code with the message and field", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({
    error: { code: "google_other_account", message: "Review this account.", field: "account" },
  }, 502));
  await expect(syncGoogleTasks()).rejects.toMatchObject({
    status: 502, code: "google_other_account", message: "Review this account.", field: "account",
  });
});
