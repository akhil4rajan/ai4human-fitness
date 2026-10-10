"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Checkin } from "@/lib/api";
import { buttonClass, Field, inputClass } from "./Field";
import TrendChart from "./TrendChart";

const series = (rows: Checkin[], key: "weight_kg" | "sleep_hours" | "mood" | "stress") =>
  rows.filter((r) => r[key] != null).map((r) => ({ label: (r.day ?? "").slice(5), value: r[key] as number }));

export default function Progress() {
  const [rows, setRows] = useState<Checkin[]>([]);
  const [form, setForm] = useState({ sleep_hours: "", mood: "", stress: "", weight_kg: "", workout_done: false });
  const [status, setStatus] = useState("");

  const load = useCallback(() => api.checkins().then(setRows).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body: Record<string, number | boolean> = { workout_done: form.workout_done };
    for (const k of ["sleep_hours", "mood", "stress", "weight_kg"] as const) {
      if (form[k] !== "") body[k] = Number(form[k]);
    }
    try {
      await api.saveCheckin(body);
      setForm({ sleep_hours: "", mood: "", stress: "", weight_kg: "", workout_done: false });
      setStatus("Check-in saved.");
      load();
    } catch {
      setStatus("Could not save. Check your values.");
    }
  }

  const f = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((x) => ({ ...x, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Progress</h1>
      <form onSubmit={submit} className="space-y-3 rounded-lg border border-border bg-surface p-4">
        <h2 className="font-medium">Today&apos;s check-in</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Field id="sleep" label="Sleep (h)"><input id="sleep" type="number" min={0} max={24} step="0.25" className={inputClass} value={form.sleep_hours} onChange={f("sleep_hours")} /></Field>
          <Field id="mood" label="Mood (1–10)"><input id="mood" type="number" min={1} max={10} className={inputClass} value={form.mood} onChange={f("mood")} /></Field>
          <Field id="stress" label="Stress (1–10)"><input id="stress" type="number" min={1} max={10} className={inputClass} value={form.stress} onChange={f("stress")} /></Field>
          <Field id="weight" label="Weight (kg)"><input id="weight" type="number" min={31} max={299} step="0.1" className={inputClass} value={form.weight_kg} onChange={f("weight_kg")} /></Field>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.workout_done} onChange={f("workout_done")} /> I worked out today
        </label>
        <div className="flex items-center gap-3">
          <button className={buttonClass}>Save check-in</button>
          <p role="status" className="text-sm text-muted">{status}</p>
        </div>
      </form>

      <div className="grid gap-4 sm:grid-cols-2">
        <TrendChart title="Sleep" unit=" h" points={series(rows, "sleep_hours")} />
        <TrendChart title="Mood" unit="/10" points={series(rows, "mood")} />
        <TrendChart title="Stress" unit="/10" points={series(rows, "stress")} />
        <TrendChart title="Weight" unit=" kg" points={series(rows, "weight_kg")} />
      </div>
    </div>
  );
}
