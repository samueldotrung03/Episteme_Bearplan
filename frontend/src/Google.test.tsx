import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Google, useGoogleChanges } from "./Google";
import type { GoogleState } from "./api";

const base: GoogleState = {
  setup: "configured", activity: "idle", connection_changing: false, pausing: false, status: "not_synced", revoked: null,
  configured: true, connected: true, sign_in_pending: false, sign_in_attempt_id: null,
  sign_in_error: null, missing_permissions: [],
  tasks: {
    last_attempt_at: null, last_success_at: null, last_error: null, paused_at: null, syncing: false,
    account_status: "unverified", account_review_key: null, other_account: false,
    synced_lists: 0, synced_tasks: 0, synced_events: 0,
  },
};

const signedOut = { ...base, connected: false, status: "signed_out" } as const;

function reply(body: unknown, status = 200, url = "") {
  if (url.endsWith("/api/google/calendars") || url.endsWith("/calendars/refresh")) body = [];
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

afterEach(() => vi.restoreAllMocks());

describe("Google", () => {
  it("explains setup when no sign-in file exists", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => reply({ ...signedOut, setup: "missing", configured: false }));
    render(<Google visible />);
    expect(await screen.findByText(/No Google sign-in file was found/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Connect Google" })).toBeNull();
  });

  it("offers a fallback when a tab is blocked and cancels only the current sign-in attempt", async ({ onTestFinished }) => {
    const url = "https://accounts.google.com/o/oauth2/auth?x=1";
    const attempt = "test-attempt";
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    let pending = false;
    let failRead = false;
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const path = String(input);
      if (path.endsWith("/connect")) {
        pending = true;
        return reply({ url, attempt_id: attempt });
      }
      if (path.endsWith("/cancel-sign-in")) {
        pending = false;
        failRead = true;
        return reply({ cancelled: true });
      }
      if (failRead) return reply({ error: { message: "Status unavailable." } }, 503);
      return reply({ ...signedOut, sign_in_pending: pending, sign_in_attempt_id: pending ? attempt : null });
    });
    const prototype = HTMLDialogElement.prototype;
    const showModal = Object.getOwnPropertyDescriptor(prototype, "showModal");
    const close = Object.getOwnPropertyDescriptor(prototype, "close");
    Object.defineProperties(prototype, {
      showModal: { configurable: true, value(this: HTMLDialogElement) { this.setAttribute("open", ""); } },
      close: { configurable: true, value(this: HTMLDialogElement) { this.removeAttribute("open"); } },
    });
    onTestFinished(() => {
      for (const [key, descriptor] of [["showModal", showModal], ["close", close]] as const) {
        if (descriptor) Object.defineProperty(prototype, key, descriptor);
        else Reflect.deleteProperty(prototype, key);
      }
    });
    const view = render(<Google visible />);
    const user = userEvent.setup();
    const trigger = await screen.findByRole("button", { name: "Connect Google" });
    await user.click(trigger);
    expect(screen.getByRole("dialog", { name: "What BearPlans shares with Google" })).toBeVisible();
    expect(screen.getByText(/including bCourses assignments you added/)).toBeVisible();
    expect(fetch.mock.calls.some(([input]) => String(input).endsWith("/connect"))).toBe(false);
    expect(open).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(trigger).toHaveFocus();
    expect(screen.queryByRole("dialog")).toBeNull();
    await user.click(trigger);
    await user.click(screen.getByRole("button", { name: "Continue with Google" }));
    expect(open).toHaveBeenCalledWith(url, "_blank", "noopener");
    expect(await screen.findByRole("link", { name: "Open Google sign-in" })).toHaveAttribute("href", url);
    view.rerender(<Google visible={false} />);
    view.rerender(<Google visible />);
    await userEvent.click(await screen.findByRole("button", { name: "Cancel sign-in" }));
    const request = fetch.mock.calls.find(([input]) => String(input).endsWith("/cancel-sign-in"));
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({ attempt_id: attempt });
    expect(await screen.findByText("Google sign-in cancelled.")).toBeVisible();
    expect(await screen.findByText(/Status unavailable/)).toBeVisible();
    expect(await screen.findByRole("button", { name: "Connect Google" })).toBeVisible();
    expect(screen.queryByRole("link", { name: "Open Google sign-in" })).toBeNull();
  });

  it("syncs now and shows counts", async () => {
    const changed = vi.fn();
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => String(input).endsWith("/tasks/sync")
      ? reply({ ...base, tasks: { ...base.tasks, account_status: "verified", synced_lists: 2, synced_tasks: 7, last_success_at: "2026-11-02T20:00:00Z" } })
      : reply(base, 200, String(input)));
    render(<Google visible onChanged={changed} />);
    await userEvent.click(await screen.findByRole("button", { name: "Sync now" }));
    expect(await screen.findByText(/7 tasks in 2 lists/)).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("Google sync finished");
    expect(changed).toHaveBeenCalled();
  });

  it("shows a failed sync and missing permissions", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => String(input).endsWith("/tasks/sync")
      ? reply({ error: { code: "google_unreachable", message: "Cannot reach Google." } }, 502)
      : reply({ ...base, missing_permissions: ["tasks"], tasks: { ...base.tasks, last_error: "Cannot reach Google." } }, 200, String(input)));
    render(<Google visible />);
    expect(await screen.findByText(/Some permissions were not given \(tasks\)/)).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Sync now" }));
    expect((await screen.findAllByRole("alert")).some((node) => node.textContent?.includes("Cannot reach Google."))).toBe(true);
  });

  it("keeps the last successful full sync and Pause visible when action and status readback both fail", async () => {
    const previous: GoogleState = {
      ...base, status: "paused",
      tasks: { ...base.tasks, last_success_at: "2026-11-02T20:00:00Z", paused_at: "2026-11-05T08:00:00Z" },
    };
    let statusReads = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/tasks/sync")) return reply({ error: { code: "google_unreachable", message: "Cannot reach Google." } }, 502);
      if (url === "/api/google" && ++statusReads === 2) return reply({ error: { message: "Status unavailable." } }, 503);
      return reply(previous, 200, url);
    });
    const user = userEvent.setup();
    render(<Google visible />);
    await user.click(await screen.findByRole("button", { name: "Sync once" }));
    expect(await screen.findByText("Cannot reach Google.")).toBeVisible();
    expect(await screen.findByText(/Connection status could not be refreshed/)).toBeVisible();
    expect(screen.getByText(/Last full sync succeeded/)).toBeVisible();
    expect(screen.getByText("Automatic sync is paused.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Retry status" }));
    await waitFor(() => expect(screen.queryByText(/Connection status could not be refreshed/)).toBeNull());
    expect(screen.getByText("Cannot reach Google.")).toBeVisible();
  });

  it("ignores an obsolete status response after leaving and returning to Google", async () => {
    let resolveOld!: (response: Response) => void;
    const old = new Promise<Response>((resolve) => { resolveOld = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockReturnValueOnce(old)
      .mockImplementation((url) => reply(signedOut, 200, String(url)));
    const view = render(<Google visible />);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    view.rerender(<Google visible={false} />);
    expect(fetch.mock.calls[0][1]?.signal?.aborted).toBe(true);
    view.rerender(<Google visible />);
    expect(await screen.findByText("Sign in to Google to continue.")).toBeVisible();
    await act(async () => resolveOld(await reply(base)));
    expect(screen.queryByText("Google sign-in is saved.")).toBeNull();
    expect(fetch.mock.calls.map(([url]) => url)).toEqual(["/api/google", "/api/google"]);
  });

  it("offers account verification when a pending create is hidden after restart", async () => {
    let verified = false;
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/verify-pending-create")) verified = true;
      return reply({ ...base, status: "needs_attention", tasks: { ...base.tasks,
        paused_at: "2026-11-06T00:00:00Z", account_status: verified ? "verified" : "unverified",
        pending_create_unverified: !verified,
        pending_create: verified ? { kind: "task", review_key: "a".repeat(32), context: "Read" } : null,
      } }, 200, url);
    });
    render(<Google visible />);
    expect(await screen.findByText(/Verify this account to see the details/)).toBeVisible();
    expect(screen.queryByText("Read")).toBeNull();
    expect(screen.getByRole("button", { name: "Sync once" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Verify Google account" }));
    expect(await screen.findByRole("button", { name: "Review uncertain Google create…" })).toBeVisible();
    expect(fetch).toHaveBeenCalledWith("/api/google/verify-pending-create", expect.objectContaining({ method: "POST" }));
  });

  it("requires an explicit review before clearing an uncertain create", async ({ onTestFinished }) => {
    const prototype = HTMLDialogElement.prototype;
    const showModal = Object.getOwnPropertyDescriptor(prototype, "showModal");
    const close = Object.getOwnPropertyDescriptor(prototype, "close");
    Object.defineProperties(prototype, {
      showModal: { configurable: true, value(this: HTMLDialogElement) { this.setAttribute("open", ""); } },
      close: { configurable: true, value(this: HTMLDialogElement) { this.removeAttribute("open"); } },
    });
    onTestFinished(() => {
      for (const [key, descriptor] of [["showModal", showModal], ["close", close]] as const) {
        if (descriptor) Object.defineProperty(prototype, key, descriptor);
        else Reflect.deleteProperty(prototype, key);
      }
    });
    const reviewKey = "a".repeat(32);
    const pendingState: GoogleState = { ...base, status: "needs_attention", tasks: {
      ...base.tasks, account_status: "verified", paused_at: "2026-11-06T00:00:00Z",
      pending_create: { kind: "task", review_key: reviewKey, context: "Read the primary source" },
    } };
    const cleared = { ...pendingState, tasks: { ...pendingState.tasks, pending_create: null } };
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input) =>
      reply(String(input).endsWith("/resolve-uncertain-create") ? cleared : pendingState, 200, String(input)));
    render(<Google visible />);
    expect(await screen.findByText(/may have been created, but BearPlans could not confirm/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Sync once" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Review uncertain Google create…" }));
    expect(screen.getByText(/a future sync may create a duplicate/)).toBeVisible();
    expect(screen.getByText("Read the primary source")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(fetch.mock.calls.some(([url]) => String(url).endsWith("/resolve-uncertain-create"))).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Review uncertain Google create…" }));
    await userEvent.click(screen.getByRole("button", { name: "Continue after review" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/google/resolve-uncertain-create", expect.objectContaining({
      method: "POST", body: JSON.stringify({ review_key: reviewKey, accept_possible_duplicate: true }),
    })));
  });

  it("distinguishes account review from a successful saved grant", async () => {
    const reviewed: GoogleState = {
      ...base, status: "needs_attention",
      tasks: { ...base.tasks, account_status: "different_account", other_account: true, account_review_key: "review-fixture" },
    };
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(() => reply(reviewed));
    render(<Google visible />);
    expect(await screen.findByText(/This account cannot use the saved Google links/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Sync now" })).toBeDisabled();
    expect(screen.queryByRole("heading", { name: "Calendars to show" })).toBeNull();
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});

describe("Google calendars to show", () => {
  it("loads cached calendars without automatic verification while sync is paused", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/calendars")) return reply([]);
      return reply({ ...base, tasks: { ...base.tasks, paused_at: "2026-11-05T08:00:00Z" } }, 200, url);
    });
    render(<Google visible />);
    await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).endsWith("/api/google/calendars"))).toBe(true));
    expect(fetch.mock.calls.some(([url]) => String(url).includes("/calendars/refresh"))).toBe(false);
    expect(screen.getByText(/each contact Google once/)).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Refresh calendars" }));
    expect(await screen.findByText(/Updated your calendar list/)).toBeTruthy();
    expect(fetch).toHaveBeenCalledWith("/api/google/calendars/refresh", expect.objectContaining({ method: "POST" }));
  });

  it("shows Pausing while Google work drains without starting a picker refresh", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input) =>
      reply(String(input).includes("/calendars") ? [] : {
        ...base, pausing: true, status: "pausing", activity: "syncing",
      }));
    render(<Google visible />);
    expect(await screen.findByText(/Pausing… Waiting for current Google work/)).toBeVisible();
    expect(screen.queryByText("Automatic sync is paused.")).toBeNull();
    expect(screen.getByRole("button", { name: "Sync now" })).toBeDisabled();
    await waitFor(() => expect(fetch.mock.calls.some(([url]) => url === "/api/google/calendars")).toBe(true));
    expect(fetch.mock.calls.some(([url]) => String(url).includes("/calendars/refresh"))).toBe(false);
  });

  it("marks empty-cache refresh on open as automatic", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input) =>
      reply(String(input).includes("/calendars") ? [] : base));
    render(<Google visible />);
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      "/api/google/calendars/refresh?automatic=true",
      expect.objectContaining({ method: "POST", signal: expect.any(AbortSignal) }),
    ));
  });

  it("lists calendars and saves the chosen ones", async () => {
    const calendars = [
      { account_key: "account-a", calendar_id: "me", summary: "Me", color: "#9fc6e7", is_primary: true, followed: false },
      { account_key: "account-a", calendar_id: "work", summary: "Lab job", color: "", is_primary: false, followed: false },
    ];
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      if (url.endsWith("/api/google/calendars") && init?.method === "PUT") return reply(calendars.map((c) => ({ ...c, followed: c.calendar_id === "work" })));
      if (url.endsWith("/api/google/calendars")) return reply(calendars);
      return reply(base);
    });
    render(<Google visible />);
    await userEvent.click(await screen.findByRole("checkbox", { name: /Lab job/ }));
    await userEvent.click(screen.getByRole("button", { name: "Save calendars" }));
    expect(fetch).toHaveBeenCalledWith("/api/google/calendars", expect.objectContaining({ method: "PUT", body: JSON.stringify({ account_key: "account-a", calendar_ids: ["work"] }) }));
    expect(await screen.findByText(/Saved your calendars/)).toBeTruthy();
    expect((screen.getByRole("checkbox", { name: /Lab job/ }) as HTMLInputElement).checked).toBe(true);
  });
});

describe("useGoogleChanges", () => {
  it("reads a baseline at mount and refreshes only after the sync version changes", async () => {
    vi.useFakeTimers();
    try {
      let version = 3;
      const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(() => reply({ version }));
      const changed = vi.fn();
      function Probe() { useGoogleChanges(changed); return null; }
      render(<Probe />);
      expect(fetch).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(0);
      expect(changed).not.toHaveBeenCalled();
      version = 4;
      await vi.advanceTimersByTimeAsync(30000);
      expect(fetch).toHaveBeenCalledTimes(2);
      expect(changed).toHaveBeenCalledTimes(1);
      version = 5;
      window.dispatchEvent(new Event("focus"));
      await vi.advanceTimersByTimeAsync(0);
      expect(changed).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });
});
