# AI4Human

A multi-agent wellness companion: nutrition, fitness, sleep & recovery and mental wellbeing specialists
coordinated by an orchestrator, with a code-level safety layer. Built on the Claude Agent SDK (FastAPI) and
Next.js. Wellness guidance only, **not medical advice**; adults (18+).

Features persistent memory, deterministic calculators, safety gating, streaming UX and production observability.

**Pitch deck (PDF):** [docs/pitch_deck.pdf](docs/pitch_deck.pdf), a non-technical overview of the problem, workflow,
strengths, architecture, components and how it can scale.

## How it works

```
Browser --SSE--> Next.js (/api proxy) --> FastAPI
                                           |- Safety gate (input)  -> vetted crisis/medical/ED response, agents never run
                                           |- Orchestrator (Claude) -> subagents: nutrition, fitness, sleep_recovery,
                                           |                           mental_wellbeing, checkin   (minimal tools each)
                                           |- Tools: calc_targets, get_profile, save_checkin, trend_summary
                                           |- Output gate (code) -> blocks <1200 kcal/day targets, dosing, diagnoses
                                           '- SQLite (profile, check-ins) + Langfuse (optional tracing)
```

- **Safety is enforced in code, not only prompts.** Crisis, eating-disorder and medical red-flag messages bypass
  the model entirely. Tools are allow-listed by a pre-tool-use hook; no shell or file tools exist.
- **Numbers come from tools**, never from the model (calorie floor included).
- **Your data stays local** (SQLite). Bring your own Anthropic key: it lives in the browser tab and is sent per
  request, never stored or logged by the server.

## Run it

Demo mode, no API key needed (canned answers, exercises the whole UI):

```bash
cd backend && pip install -e ".[dev]" && AI4HUMAN_FAKE_RUNNER=1 uvicorn app.main:app --port 8000
cd frontend && npm ci && npm run dev          # http://localhost:3000  (proxies /api to :8000)
```

Real answers: start the backend without `AI4HUMAN_FAKE_RUNNER`, open **Settings** and paste your Anthropic key.

Docker (not yet built or tested in CI; see Status): `cp .env.example .env && docker compose up --build`.

## Docs

[Architecture](docs/architecture.md) (diagrams) · [Safety](docs/safety.md) · [Evals](docs/evals.md) ·
[Observability](docs/observability.md) · [CLAUDE.md](CLAUDE.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

## Observability (Langfuse, optional)

Set `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL`. See [docs/observability.md](docs/observability.md).
Health conversations are sensitive, so **prompt, answer and tool content is stripped from traces by default**.

## Tests

```bash
cd backend && pytest -q && ruff check .      # 52 offline tests (incl. offline evals), no network
cd backend && python -m evals.run            # safety/output-gate/calorie evals; see docs/evals.md
cd frontend && npm run typecheck && npm run lint && npm test && npm run build
cd frontend && npx playwright test           # browser smoke test against fake-runner backend
```

## Status

Verified: backend unit/API tests, frontend type/lint/unit/build, browser smoke test (including SSE through the
Next proxy), Langfuse span export and masking against an in-memory exporter.

**Not yet verified:** anything against the live model or a live Langfuse project (no keys were available while
building); Docker images (no daemon available); that `tools=["Agent"]` keeps subagent delegation working; the
exact deny shape of the tool hook against the real CLI. Run one real chat turn before relying on it.
Offline evals exist (docs/evals.md); live specialist-quality evals are written but have not been run.

## Roadmap

Run the live evals and record a baseline, push scores to Langfuse; add an LLM second-stage safety classifier (the rule-based
input gate misses indirect phrasing, see docs/evals.md);
structured `DailyPlan` output and weekly review; prompt versioning in Langfuse; wearables import.
