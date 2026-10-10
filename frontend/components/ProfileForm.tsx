"use client";

import { useEffect, useState } from "react";
import { api, type Activity, type Goal, type Profile, type Targets } from "@/lib/api";
import { buttonClass, Field, inputClass } from "./Field";

const EMPTY: Profile = {
  sex: "female", age: 30, weight_kg: 70, height_cm: 170, activity: "light", goal: "maintain",
  diet: "", injuries: "", notes: "",
};

export default function ProfileForm() {
  const [p, setP] = useState<Profile>(EMPTY);
  const [targets, setTargets] = useState<Targets | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    api.profile().then((saved) => {
      if (saved.age) setP({ ...EMPTY, ...saved });
    }).catch(() => {});
  }, []);

  const valid = p.age >= 18 && p.age <= 100 && p.weight_kg > 30 && p.weight_kg < 300 && p.height_cm > 120 && p.height_cm < 250;

  const { sex, age, weight_kg, height_cm, activity, goal } = p;
  useEffect(() => {
    if (!valid) return;
    const t = setTimeout(() => {
      api.targets({ sex, age, weight_kg, height_cm, activity, goal }).then(setTargets).catch(() => setTargets(null));
    }, 300);
    return () => clearTimeout(t);
  }, [sex, age, weight_kg, height_cm, activity, goal, valid]);

  const set = <K extends keyof Profile>(k: K, v: Profile[K]) => setP((x) => ({ ...x, [k]: v }));
  const num = (k: "age" | "weight_kg" | "height_cm") => (e: React.ChangeEvent<HTMLInputElement>) => set(k, Number(e.target.value));

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    setStatus("Saving…");
    try {
      await api.saveProfile(p);
      setStatus("Saved. Your assistant will use this profile.");
    } catch {
      setStatus("Could not save. Check your values.");
    }
  }

  return (
    <form onSubmit={save} className="space-y-4">
      <h1 className="text-xl font-semibold">Your profile</h1>
      <p className="text-sm text-muted">
        Stored only on this machine. This app is for adults (18+). If you are pregnant, managing a medical
        condition, or recovering from an injury, check plans with a doctor or registered dietitian first.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="sex" label="Sex (for calorie formulas)">
          <select id="sex" className={inputClass} value={p.sex} onChange={(e) => set("sex", e.target.value as Profile["sex"])}>
            <option value="female">Female</option>
            <option value="male">Male</option>
          </select>
        </Field>
        <Field id="age" label="Age" hint={p.age < 18 ? "You must be 18 or older to use this app." : undefined}>
          <input id="age" type="number" min={18} max={100} className={inputClass} value={p.age} onChange={num("age")} />
        </Field>
        <Field id="weight" label="Weight (kg)">
          <input id="weight" type="number" min={31} max={299} step="0.1" className={inputClass} value={p.weight_kg} onChange={num("weight_kg")} />
        </Field>
        <Field id="height" label="Height (cm)">
          <input id="height" type="number" min={121} max={249} className={inputClass} value={p.height_cm} onChange={num("height_cm")} />
        </Field>
        <Field id="activity" label="Activity level">
          <select id="activity" className={inputClass} value={p.activity} onChange={(e) => set("activity", e.target.value as Activity)}>
            <option value="sedentary">Sedentary (desk job, little exercise)</option>
            <option value="light">Light (1–3 workouts/week)</option>
            <option value="moderate">Moderate (3–5 workouts/week)</option>
            <option value="active">Active (6–7 workouts/week)</option>
            <option value="very_active">Very active (physical job + training)</option>
          </select>
        </Field>
        <Field id="goal" label="Goal">
          <select id="goal" className={inputClass} value={p.goal} onChange={(e) => set("goal", e.target.value as Goal)}>
            <option value="lose">Lose weight gradually</option>
            <option value="maintain">Maintain</option>
            <option value="gain">Build / gain</option>
          </select>
        </Field>
        <Field id="diet" label="Diet preferences / allergies">
          <input id="diet" className={inputClass} maxLength={200} value={p.diet} onChange={(e) => set("diet", e.target.value)} placeholder="e.g. vegetarian, no nuts" />
        </Field>
        <Field id="injuries" label="Injuries / limitations">
          <input id="injuries" className={inputClass} maxLength={500} value={p.injuries} onChange={(e) => set("injuries", e.target.value)} placeholder="e.g. sore left knee" />
        </Field>
      </div>

      {valid && targets && (
        <section aria-label="Estimated targets" className="rounded-lg border border-border bg-surface p-4">
          <h2 className="font-medium">Estimated daily targets</h2>
          <dl className="mt-2 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div><dt className="text-muted">Calories</dt><dd className="text-lg font-semibold">{targets.kcal}</dd></div>
            <div><dt className="text-muted">Protein</dt><dd className="text-lg font-semibold">{targets.macros.protein_g} g</dd></div>
            <div><dt className="text-muted">Carbs</dt><dd className="text-lg font-semibold">{targets.macros.carb_g} g</dd></div>
            <div><dt className="text-muted">Fat</dt><dd className="text-lg font-semibold">{targets.macros.fat_g} g</dd></div>
          </dl>
          <p className="mt-2 text-xs text-muted">Estimates only (maintenance ≈ {targets.tdee} kcal, BMI {targets.bmi}). Never below a safe minimum.</p>
        </section>
      )}

      <div className="flex items-center gap-3">
        <button className={buttonClass} disabled={!valid}>Save profile</button>
        <p role="status" className="text-sm text-muted">{status}</p>
      </div>
    </form>
  );
}
