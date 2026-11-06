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

  it("opens Google sign-in in a new tab", async () => {
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/connect")) return reply({ url: "https://accounts.google.com/o/oauth2/auth?x=1", attempt_id: "test-attempt" });
      return reply(signedOut);
    });
    render(<Google visible />);
    await userEvent.click(await screen.findByRole("button", { name: "Connect Google" }));
    await waitFor(() => expect(open).toHaveBeenCalledWith("https://accounts.google.com/o/oauth2/auth?x=1", "_blank", "noopener"));
    expect(await screen.findByText(/sign-in opened in a new tab/)).toBeTruthy();
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

  it("uses the Disconnect receipt to distinguish unconfirmed remote revocation", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      return url.endsWith("/disconnect")
        ? reply({ ...signedOut, revoked: false })
        : reply({ ...base, tasks: { ...base.tasks, paused_at: "2026-11-05T08:00:00Z" } }, 200, url);
    });
    render(<Google visible />);
    await userEvent.click(await screen.findByRole("button", { name: "Disconnect" }));
    expect(await screen.findByRole("status")).toHaveTextContent("could not confirm that Google revoked access");
    expect(screen.getByText("Sign in to Google to continue.")).toBeVisible();
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
  it("refreshes only after the sync version changes, never at mount", async () => {
    vi.useFakeTimers();
    try {
      let version = 3;
      const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(() => reply({ version }));
      const changed = vi.fn();
      function Probe() { useGoogleChanges(changed); return null; }
      render(<Probe />);
      expect(fetch).not.toHaveBeenCalled();
      await vi.advanceTimersByTimeAsync(30000);
      expect(fetch).toHaveBeenCalledTimes(1);
      expect(changed).not.toHaveBeenCalled();
      await vi.advanceTimersByTimeAsync(30000);
      expect(changed).not.toHaveBeenCalled();
      version = 4;
      window.dispatchEvent(new Event("focus"));
      await vi.advanceTimersByTimeAsync(0);
      expect(changed).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });
});
