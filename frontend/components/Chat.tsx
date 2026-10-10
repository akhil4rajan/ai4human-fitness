"use client";

import { useEffect, useRef, useState } from "react";
import { api, chat } from "@/lib/api";
import Markdown from "./Markdown";

interface Msg {
  id: string;
  role: "user" | "assistant";
  text: string;
  kind?: "safety" | "error";
  specialists?: string[];
  meta?: string;
  rated?: 1 | -1;
}

const LABELS: Record<string, string> = {
  nutrition: "Nutrition",
  fitness: "Fitness",
  sleep_recovery: "Sleep & recovery",
  mental_wellbeing: "Mental wellbeing",
  checkin: "Check-in",
};
const label = (n: string) => LABELS[n] ?? n;
const uid = () => crypto.randomUUID();

const SUGGESTIONS = [
  "Plan my week of meals and workouts",
  "I'm sleeping badly and feel stressed. Should I train today?",
  "How much protein should I eat?",
];

export default function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [consulting, setConsulting] = useState<string[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [msgs, consulting]);

  useEffect(() => () => abortRef.current?.abort(), []);

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    setInput("");
    setBusy(true);
    setConsulting([]);
    setMsgs((m) => [...m, { id: uid(), role: "user", text: message }]);
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const reply = (patch: Omit<Msg, "id" | "role">) =>
      setMsgs((m) => [...m, { id: uid(), role: "assistant", ...patch }]);
    try {
      let got = false;
      for await (const ev of chat(message, ctrl.signal)) {
        got = true;
        if (ev.type === "specialist") setConsulting((c) => (c.includes(ev.name) ? c : [...c, ev.name]));
        else if (ev.type === "safety") reply({ text: ev.text, kind: "safety" });
        else if (ev.type === "error") reply({ text: ev.text, kind: "error" });
        else if (ev.type === "final") {
          const secs = (ev.latency_ms / 1000).toFixed(1);
          const cost = ev.cost_usd != null ? ` · $${ev.cost_usd.toFixed(3)}` : "";
          reply({ text: ev.text, specialists: ev.specialists, meta: `${secs}s${cost}` });
        }
      }
      if (!got) reply({ text: "No response received. Please try again.", kind: "error" });
    } catch (e) {
      if ((e as Error).name !== "AbortError") reply({ text: "Connection lost. Please try again.", kind: "error" });
    } finally {
      setConsulting([]);
      setBusy(false);
    }
  }

  function rate(id: string, rating: 1 | -1) {
    setMsgs((m) => m.map((x) => (x.id === id ? { ...x, rated: rating } : x)));
    api.feedback(id, rating).catch(() => {});
  }

  return (
    <div className="flex min-h-[70vh] flex-col">
      <div className="flex-1 space-y-4" role="log" aria-live="polite" aria-label="Conversation">
        {msgs.length === 0 && (
          <section className="rounded-lg border border-border bg-surface p-4">
            <h1 className="text-lg font-semibold">How can I support your health today?</h1>
            <p className="mt-1 text-sm text-muted">
              A team of nutrition, fitness, sleep and wellbeing specialists works together on your question. Add
              your Anthropic API key in Settings and fill in your Profile for personalised answers.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-border px-3 py-1.5 text-sm hover:bg-background"
                >
                  {s}
                </button>
              ))}
            </div>
          </section>
        )}

        {msgs.map((m) =>
          m.role === "user" ? (
            <div key={m.id} className="flex justify-end">
              <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-accent px-4 py-2 text-accent-contrast">
                {m.text}
              </p>
            </div>
          ) : m.kind === "safety" ? (
            <section
              key={m.id}
              role="alert"
              className="rounded-lg border-2 border-[var(--danger-border)] bg-[var(--danger-bg)] p-4"
            >
              <h2 className="font-semibold">Support is available</h2>
              <p className="mt-1 whitespace-pre-wrap text-sm">{m.text}</p>
            </section>
          ) : (
            <div key={m.id} className="max-w-[92%]">
              <div
                className={`rounded-2xl border px-4 py-3 ${
                  m.kind === "error" ? "border-[var(--danger-border)] bg-[var(--danger-bg)]" : "border-border bg-surface"
                }`}
              >
                {m.kind === "error" ? m.text : <Markdown>{m.text}</Markdown>}
              </div>
              {m.kind !== "error" && (
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
                  {m.specialists?.map((s) => (
                    <span key={s} className="rounded-full border border-border px-2 py-0.5">
                      {label(s)}
                    </span>
                  ))}
                  {m.meta && <span>{m.meta}</span>}
                  <span className="ml-auto flex gap-1">
                    {([1, -1] as const).map((r) => (
                      <button
                        key={r}
                        onClick={() => rate(m.id, r)}
                        disabled={m.rated !== undefined}
                        aria-label={r === 1 ? "Helpful" : "Not helpful"}
                        aria-pressed={m.rated === r}
                        className={`rounded px-2 py-1 hover:bg-background ${m.rated === r ? "bg-background font-bold" : ""}`}
                      >
                        {r === 1 ? "👍" : "👎"}
                      </button>
                    ))}
                  </span>
                </div>
              )}
            </div>
          ),
        )}

        {busy && (
          <p className="text-sm text-muted" role="status">
            {consulting.length ? `Consulting ${consulting.map(label).join(", ")}…` : "Thinking…"}
          </p>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="sticky bottom-0 mt-4 flex gap-2 bg-background py-3"
      >
        <label htmlFor="msg" className="sr-only">
          Message
        </label>
        <textarea
          id="msg"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(input);
            }
          }}
          maxLength={4000}
          rows={2}
          placeholder="Ask about food, training, sleep or how you're feeling…"
          className="flex-1 resize-none rounded-lg border border-border bg-surface px-3 py-2"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-lg bg-accent px-4 font-medium text-accent-contrast disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
