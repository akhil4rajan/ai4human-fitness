import { parseSSE } from "./sse";

export type Activity = "sedentary" | "light" | "moderate" | "active" | "very_active";
export type Goal = "lose" | "maintain" | "gain";

export interface Profile {
  sex: "male" | "female";
  age: number;
  weight_kg: number;
  height_cm: number;
  activity: Activity;
  goal: Goal;
  diet: string;
  injuries: string;
  notes: string;
}

export interface Targets {
  tdee: number;
  kcal: number;
  macros: { protein_g: number; fat_g: number; carb_g: number };
  bmi: number;
}

export interface Checkin {
  id?: number;
  day?: string;
  weight_kg: number | null;
  sleep_hours: number | null;
  mood: number | null;
  stress: number | null;
  workout_done: boolean | number | null;
  notes: string | null;
}

export type ChatEvent =
  | { type: "safety"; text: string; category?: string }
  | { type: "specialist"; name: string }
  | {
      type: "final";
      text: string;
      specialists: string[];
      latency_ms: number;
      cost_usd: number | null;
      turn_id?: string;
    }
  | { type: "error"; text: string };

const KEY_STORAGE = "ai4human.anthropic_key";

export function getApiKey(): string {
  try {
    return sessionStorage.getItem(KEY_STORAGE) ?? "";
  } catch {
    return "";
  }
}

export function setApiKey(key: string): void {
  try {
    if (key) sessionStorage.setItem(KEY_STORAGE, key);
    else sessionStorage.removeItem(KEY_STORAGE);
  } catch {
    /* storage unavailable: key lives only for this call chain */
  }
}

/** Anonymous per-tab id used only to group one visit's traces. No account, no personal data. */
function sessionId(): string {
  try {
    let id = sessionStorage.getItem("ai4human.session");
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem("ai4human.session", id);
    }
    return id;
  } catch {
    return "";
  }
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export const api = {
  profile: () => fetch("/api/profile").then((r) => json<Partial<Profile>>(r)),
  saveProfile: (p: Profile) =>
    fetch("/api/profile", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify(p) }).then((r) =>
      json<Profile>(r),
    ),
  targets: (p: Pick<Profile, "sex" | "age" | "weight_kg" | "height_cm" | "activity" | "goal">) =>
    fetch("/api/targets", { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(p) }).then((r) =>
      json<Targets>(r),
    ),
  checkins: () => fetch("/api/checkins?days=60").then((r) => json<Checkin[]>(r)),
  saveCheckin: (c: Partial<Checkin>) =>
    fetch("/api/checkins", { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(c) }).then((r) =>
      json<{ saved: boolean }>(r),
    ),
  feedback: (turn_id: string, rating: 1 | -1) =>
    fetch("/api/feedback", { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ turn_id, rating }) }),
  exportData: () => fetch("/api/export").then((r) => json<unknown>(r)),
  deleteData: () => fetch("/api/data", { method: "DELETE" }).then((r) => json<{ deleted: boolean }>(r)),
};

/** POST a chat message and yield orchestrator events as they stream in. */
export async function* chat(message: string, signal?: AbortSignal): AsyncGenerator<ChatEvent> {
  const key = getApiKey();
  const sid = sessionId();
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: {
      ...JSON_HEADERS,
      ...(key ? { "X-Anthropic-Key": key } : {}),
      ...(sid ? { "X-Session-Id": sid } : {}),
    },
    body: JSON.stringify({ message }),
    signal,
  });
  if (!res.ok || !res.body) {
    yield { type: "error", text: res.status === 422 ? "That message can't be sent." : "Something went wrong." };
    return;
  }
  yield* parseSSE<ChatEvent>(res.body);
}
