# CLAUDE.md

Guidance for Claude Code (and humans) working in this repo. Keep it short; link to `docs/` for depth.

## What this is
AI4Human: a multi-agent **wellness** companion (nutrition, fitness, sleep & recovery, mental wellbeing, check-ins).
FastAPI backend using the Claude Agent SDK, Next.js frontend. Wellness guidance only, **not medical advice**;
adults (18+). Single-user, local-first demo: bring-your-own Anthropic key, SQLite, no accounts.
See `docs/architecture.md`, `docs/safety.md`, `docs/evals.md`, `docs/observability.md`.

## Layout
```
backend/app/        main.py (FastAPI), orchestrator.py, chat_service.py, agents/definitions.py,
                    tools/{calculators,server}.py, safety/{rules,resources,gate,hooks}.py,
                    memory/db.py (SQLite), observability.py (Langfuse), logging_setup.py, ratelimit.py
backend/evals/      datasets/*.jsonl, suites.py, run.py   (offline gates CI; live needs a key)
backend/tests/      offline tests, fake runner, no network
frontend/           Next.js 16 App Router: app/, components/, lib/{api,sse}.ts, e2e/ (Playwright)
docs/  .github/workflows/ci.yml  docker-compose.yml  .env.example
```

## Commands
```bash
# backend (from backend/)
pip install -e ".[dev]"
pytest -q                                   # ~50 offline tests incl. the offline evals
ruff check .
python -m evals.run                         # offline evals (gated); add --suite live with ANTHROPIC_API_KEY
AI4HUMAN_FAKE_RUNNER=1 uvicorn app.main:app --port 8000   # demo mode, no key, no cost

# frontend (from frontend/)
npm ci && npm run dev                       # proxies /api to BACKEND_URL (default http://127.0.0.1:8000)
npm run typecheck && npm run lint && npm test && npm run build
npx playwright test                         # e2e against the fake-runner backend (set CHROMIUM_PATH locally)
```
CI (`.github/workflows/ci.yml`) runs ruff + pytest, typecheck/lint/vitest/build, then Playwright e2e.

## Non-negotiable rules
1. **Safety lives in code, not just prompts.** Input gate (`safety/rules.py`) runs before any model call; output gate
   (`safety/hooks.py`) and the tool allow-list hook run on every turn. Never weaken them to make a test pass.
   Any change to `rules.py`, `hooks.py`, `resources.py` or agent prompts needs `python -m evals.run` to pass.
2. **Numbers come from tools** (`calc_targets`), never from the model. The calorie floor is enforced in
   `calculators.py` (`CALORIE_FLOOR`) and re-checked on output.
3. **No health content in logs or traces.** Don't log message bodies, profiles, tool I/O or API keys. Langfuse export
   masks content with an allow-list (`observability.mask_otel_spans`); new span attributes are dropped by default.
4. **The BYO API key** arrives per request (`X-Anthropic-Key`), is passed via the SDK `env`, and is never stored.
5. **Agents get minimal tools**; no Bash/Read/Write. Tool names are `mcp__health__<tool>`.
6. Don't present a model's advice as verified: label unverified behavior as unverified.

## Gotchas (each one cost time)
- **Resolve the SDK query lazily.** Tracing instrumentation reassigns `claude_agent_sdk.query` after import, so
  `run_turn` looks it up at call time. Don't `from claude_agent_sdk import query` and bind it early.
- **Root `.gitignore` ignores `lib/`** (Python template). `frontend/lib/` is explicitly un-ignored; don't undo that.
- **Verify in a fresh clone.** Local runs have ignored/generated files (`.next/types`, `next-env.d.ts`) that CI lacks.
  `typecheck` runs `next typegen` first because `LayoutProps` is a generated type.
- **Next.js 16 differs from older versions** (Cache Components, route types). Read `frontend/AGENTS.md` and
  `frontend/node_modules/next/dist/docs/` before changing Next config or routing. SSE needs `compress: false`.
- **Langfuse clients are cached per public key**; tests must use a unique key per client or flush/shutdown hangs.
- Langfuse tags can only be set at trace start; dynamic facts go in span metadata and scores.
- Python `@tool` handlers return only `content`/`is_error` (no `structuredContent`).
- The Agent SDK bundles the Claude Code CLI inside the wheel (~240 MB); no Node needed in the backend image.

## Status / known gaps
Verified offline only. **Not verified:** real-model behavior (subagent delegation with `tools=["Agent"]`, hook deny
shape), live Langfuse, Docker image builds. The rule-based input gate misses indirect phrasings (see
`docs/evals.md`, hard tier). Check `docs/evals.md` before claiming safety coverage.

## Conventions
Python 3.11+, ruff (line length 100), type hints, small modules. TypeScript strict, ESLint (Next config), Tailwind
with CSS-variable tokens in `globals.css`. Commit messages: imperative summary + why. Branch: develop on the
session branch; open PRs only when asked.
