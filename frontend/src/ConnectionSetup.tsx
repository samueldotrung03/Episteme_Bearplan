import { useId, useLayoutEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { ApiError, saveBCoursesToken, saveGoogleClient } from "./api";

export type SetupProvider = "bCourses" | "Google";

export function ConnectionDialog({ title, busy, onDismiss, children }: {
  title: string;
  busy: boolean;
  onDismiss: () => void;
  children: ReactNode;
}) {
  const id = useId();
  const dialog = useRef<HTMLDialogElement>(null);

  useLayoutEffect(() => {
    const node = dialog.current!;
    const trigger = document.activeElement;
    node.showModal();
    return () => {
      node.close();
      if (trigger instanceof HTMLElement && trigger.isConnected) trigger.focus({ preventScroll: true });
    };
  }, []);

  return <dialog ref={dialog} className="connection-dialog" aria-labelledby={id} onCancel={(event) => {
    event.preventDefault();
    if (!busy) onDismiss();
  }}>
    <h3 id={id}>{title}</h3>
    {children}
  </dialog>;
}

export function ConnectionSetup({ provider, onDismiss, onSaved }: {
  provider: SetupProvider;
  onDismiss: () => void;
  onSaved: (notice?: string) => void;
}) {
  const token = provider === "bCourses";
  const errorId = useId();
  const field = useRef<HTMLInputElement>(null);
  const inFlight = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(false);

  useLayoutEffect(() => {
    if (error && !busy) field.current?.focus();
  }, [error, busy]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current || !field.current) return;
    const input = field.current;
    const file = input.files?.[0];
    if (file && (!file.name.toLowerCase().endsWith(".json") || file.size > 16 * 1024)) {
      setError(file.size > 16 * 1024 ? "Choose a Google Desktop app sign-in file of 16 KB or less." : "Choose the downloaded Google Desktop app JSON file.");
      return;
    }
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      if (token) await saveBCoursesToken(input.value);
      else if (file) await saveGoogleClient(await file.text());
      onSaved();
    } catch (caught) {
      if (token && caught instanceof ApiError && caught.code === "bcourses_token_saved_check_unrecorded") {
        onSaved(caught.message);
        return;
      }
      setError(caught instanceof ApiError ? caught.message : "Could not confirm the save. Check the selected input and try again.");
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  return <ConnectionDialog title={token ? "Set up bCourses token" : "Set up Google sign-in file"} busy={busy} onDismiss={onDismiss}>
    <p className="muted">{token
      ? "In bCourses, open Account → Settings → New Access Token, then paste the new token here."
      : "Choose the OAuth JSON file you downloaded for a Desktop app. Saving the file is a separate step from signing in."}</p>
    <form onSubmit={save} aria-busy={busy}>
      <label className="connection-field">
        {token ? "New bCourses token" : "Google Desktop app JSON file"}
        <input ref={field} type={token ? "password" : "file"} autoComplete="off" autoFocus required
          maxLength={token ? 512 : undefined} accept={token ? undefined : ".json,application/json"}
          disabled={busy} aria-invalid={error ? true : undefined} aria-describedby={error ? errorId : undefined}
          onChange={(event) => {
            setSelected(token ? Boolean(event.currentTarget.value.trim()) : Boolean(event.currentTarget.files?.length));
            setError("");
          }} />
      </label>
      {error ? <p id={errorId} className="error" role="alert">{error}</p> : null}
      <div className="form-actions">
        <button type="submit" disabled={busy || !selected}>{busy ? "Saving…" : token ? "Check and save" : "Save sign-in file"}</button>
        <button type="button" className="secondary" disabled={busy} onClick={onDismiss}>Cancel</button>
      </div>
      {busy ? <p role="status">Waiting for BearPlans to confirm the save…</p> : null}
    </form>
  </ConnectionDialog>;
}
