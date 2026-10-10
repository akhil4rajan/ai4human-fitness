"use client";

import { useEffect, useRef, useState } from "react";
import { api, getApiKey, setApiKey } from "@/lib/api";
import { buttonClass, Field, inputClass } from "./Field";

export default function SettingsPanel() {
  const keyRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState("");

  // sessionStorage is browser-only, so hydrate the uncontrolled input after mount.
  useEffect(() => {
    if (keyRef.current) keyRef.current.value = getApiKey();
  }, []);

  async function exportData() {
    try {
      const data = await api.exportData();
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const a = Object.assign(document.createElement("a"), { href: url, download: "ai4human-export.json" });
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setStatus("Export failed.");
    }
  }

  async function deleteAll() {
    if (!window.confirm("Delete your profile and all check-ins from this machine? This cannot be undone.")) return;
    try {
      await api.deleteData();
      setStatus("All local data deleted.");
    } catch {
      setStatus("Delete failed.");
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-xl font-semibold">Settings</h1>

      <section className="space-y-3">
        <h2 className="font-medium">Anthropic API key</h2>
        <Field id="key" label="API key" hint="Kept only in this browser tab (session storage) and sent with each chat request. The server never stores or logs it.">
          <input id="key" type="password" autoComplete="off" className={inputClass} ref={keyRef} placeholder="sk-ant-…" />
        </Field>
        <button className={buttonClass} onClick={() => { const k = keyRef.current?.value.trim() ?? ""; setApiKey(k); setStatus(k ? "Key saved for this tab." : "Key cleared."); }}>
          Save key
        </button>
      </section>

      <section className="space-y-3">
        <h2 className="font-medium">Your data</h2>
        <p className="text-sm text-muted">Your profile and check-ins live in a local database on the machine running this app. Messages go to Anthropic to generate answers. If the operator enabled Langfuse tracing, message text is redacted by default.</p>
        <div className="flex gap-3">
          <button className="rounded-lg border border-border px-4 py-2" onClick={exportData}>Export my data</button>
          <button className="rounded-lg border-2 border-[var(--danger-border)] px-4 py-2" onClick={deleteAll}>Delete all my data</button>
        </div>
      </section>
      <p role="status" className="text-sm text-muted">{status}</p>
    </div>
  );
}
