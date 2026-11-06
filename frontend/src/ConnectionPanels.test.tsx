import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { ConnectionPanels } from "./ConnectionPanels";
import * as api from "./api";

afterEach(() => vi.restoreAllMocks());

const timestamp = "2026-11-06T12:00:00Z";
const token = { set: true, saved_at: timestamp, checked_at: timestamp, check_ok: true, check_message: null };
const credentials = { folder: "", bcourses: token, google: { ...token, setup: "configured", connected: true, revoked: null } } as const;
const working: api.GoogleState = {
  setup: "configured", activity: "idle", connection_changing: false, pausing: false, status: "working",
  configured: true, connected: true, revoked: null, sign_in_pending: false, sign_in_attempt_id: null,
  sign_in_error: null, missing_permissions: [],
  tasks: {
    last_attempt_at: timestamp, last_success_at: timestamp, last_error: null, paused_at: null, syncing: false,
    account_status: "verified", account_review_key: null, other_account: false, synced_lists: 1, synced_tasks: 2, synced_events: 0,
  },
};

function mockStatus(google = working) {
  vi.spyOn(api, "getConnections").mockResolvedValue(credentials);
  vi.spyOn(api, "getGoogle").mockResolvedValue(google);
}

it("acknowledges Pause only after the service confirms it, then syncs once and resumes", async () => {
  mockStatus();
  const paused: api.GoogleState = { ...working, status: "paused", tasks: { ...working.tasks, paused_at: timestamp } };
  let confirmPause!: (state: api.GoogleState) => void;
  const change = vi.spyOn(api, "setGoogleSyncPaused")
    .mockImplementationOnce(() => new Promise((resolve) => { confirmPause = resolve; }))
    .mockResolvedValueOnce(working);
  const sync = vi.spyOn(api, "syncGoogleTasks")
    .mockRejectedValueOnce(new api.ApiError("Google is offline. Try again."))
    .mockResolvedValueOnce(paused);
  const onSynced = vi.fn();
  const user = userEvent.setup();
  render(<ConnectionPanels visible credentialVersion={0} onSetup={vi.fn()} onSynced={onSynced} onTokenRemoved={vi.fn()} />);

  const pause = await screen.findByRole("button", { name: "Pause automatic sync" });
  await user.click(pause);
  expect(screen.getByText("Pausing automatic sync…")).toBeVisible();
  expect(screen.queryByText("Automatic sync is paused.")).toBeNull();
  expect(pause).toBeDisabled();
  expect(change).toHaveBeenCalledExactlyOnceWith(true);
  await act(async () => confirmPause(paused));

  const once = screen.getByRole("button", { name: "Sync once" });
  await user.click(once);
  expect(await screen.findByText("Google is offline. Try again.")).toBeVisible();
  expect(screen.getByText("Automatic sync is paused.")).toBeVisible();
  expect(screen.getByText(/Last full sync/)).toBeVisible();
  await user.click(once);
  expect(await screen.findByText("Google sync finished.")).toBeVisible();
  expect(sync).toHaveBeenCalledTimes(2);
  expect(onSynced).toHaveBeenCalledTimes(1);
  expect(screen.getByText("Automatic sync is paused.")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Resume automatic sync" }));
  expect(await screen.findByText("Automatic sync is enabled.")).toBeVisible();
  expect(change).toHaveBeenLastCalledWith(false);
});

it("keeps provider evidence when status fails and retries the read", async () => {
  mockStatus({ ...working, status: "signed_out", connected: false });
  const read = vi.mocked(api.getGoogle);
  read.mockRejectedValueOnce(new api.ApiError("Service unavailable."))
    .mockResolvedValueOnce({ ...working, status: "signed_out", connected: false });
  const user = userEvent.setup();
  render(<ConnectionPanels visible credentialVersion={0} onSetup={vi.fn()} onSynced={vi.fn()} onTokenRemoved={vi.fn()} />);
  expect(await screen.findByText("Token saved")).toBeVisible();
  expect(await screen.findByText(/Could not refresh Google status/)).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Retry connection status" }));
  expect(await screen.findByText("Sign-in needed")).toBeVisible();
  expect(screen.getByText("Desktop sign-in file saved")).toBeVisible();
  expect(screen.queryByRole("button", { name: "Sync now" })).toBeNull();
});
