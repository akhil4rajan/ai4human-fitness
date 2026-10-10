# Architecture

Status: describes what is implemented in this repo. Items marked *planned* are not built yet.

## 1. System context

```mermaid
flowchart LR
    user([User]) -->|browser| web["Next.js app<br/>chat, profile, progress, settings"]
    web -->|"/api proxy, SSE"| api["FastAPI backend"]
    api -->|"Agent SDK (bundled Claude Code CLI)"| claude[("Anthropic API<br/>user's own key")]
    api --> db[("SQLite<br/>profile, check-ins, feedback")]
    api -. "optional, content masked" .-> lf[("Langfuse")]
    classDef ext fill:#eef,stroke:#88a
    class claude,lf ext
```

The browser only talks to the Next.js origin; `next.config.ts` rewrites `/api/*` to FastAPI (`BACKEND_URL`).
Compression is off so the SSE chat stream is not buffered.

## 2. One chat turn

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as FastAPI /api/chat
    participant S as chat_service (producer task)
    participant G as Safety gate (input)
    participant O as Orchestrator (Claude)
    participant X as Specialist subagents
    participant T as Tools (health MCP)
    participant OG as Output gate

    B->>A: POST message (X-Anthropic-Key, X-Session-Id)
    A->>S: stream_turn()  (rate limited per IP)
    S->>G: classify(message)
    alt crisis / medical / eating disorder
        G-->>B: safety event (vetted text, no model call)
    else safe
        S->>O: query() with profile, agents, tools, hooks
        O->>X: Agent tool, specialists in parallel
        X->>T: calc_targets, get_profile, trend_summary, save_checkin
        T-->>X: deterministic results
        X-->>O: findings (final message only)
        O-->>S: synthesized answer (ResultMessage)
        S->>OG: enforce_output()
        OG-->>B: final event (text, specialists, latency, cost, turn_id)
    end
    Note over B,S: events stream as SSE: specialist, safety, final, error
```

The whole turn, including the Langfuse trace, runs inside one producer task that feeds an `asyncio.Queue`; the HTTP
generator only reads the queue. This keeps OpenTelemetry context from being held across `yield`s.

## 3. Safety layers (defense in depth)

```mermaid
flowchart TB
    m[User message] --> L1["1. Input gate<br/>regex rules, runs before any model call"]
    L1 -->|blocked| r["Vetted static response<br/>988, emergency, ED resources"]
    L1 -->|ok| L2["2. Agent prompts<br/>SAFETY_PREAMBLE: no diagnosis, no doses, use calculators"]
    L2 --> L3["3. Tool allow-list hook<br/>PreToolUse denies anything else"]
    L3 --> L4["4. Deterministic tools<br/>calorie floor in code"]
    L4 --> L5["5. Output gate<br/>blocks under-floor kcal, dosing, diagnoses; adds disclaimer"]
    L5 --> out[Answer]
    L6["6. Limits: max_turns, budget, rate limit, subagent depth/concurrency"] -.-> L2
```

Details and known gaps: [safety.md](safety.md).

## 4. Components

| Component | Responsibility | Files |
|---|---|---|
| API | HTTP endpoints, SSE, request validation | `backend/app/main.py` |
| Chat service | Runs a turn inside a trace, queue to stream | `chat_service.py` |
| Orchestrator | Builds SDK options, maps messages to events | `orchestrator.py` |
| Specialists | `nutrition`, `fitness`, `sleep_recovery`, `mental_wellbeing`, `checkin` | `agents/definitions.py` |
| Tools | `calc_targets`, `get_profile`, `save_checkin`, `trend_summary` | `tools/` |
| Safety | rules, resources, gate, hooks | `safety/` |
| Memory | SQLite store | `memory/db.py` |
| Observability | Langfuse init, masking, scores | `observability.py` |
| Ops | JSON logs + request id, rate limit | `logging_setup.py`, `ratelimit.py` |
| Frontend | pages, SSE client, charts | `frontend/` |

### Models and limits
Orchestrator `claude-sonnet-5-5`; specialists `sonnet` (check-in uses `haiku`). Per turn: `max_turns=12`,
`max_budget_usd=1.0`, subagent depth 1, concurrency 4. Chat rate limit: `CHAT_RATE_LIMIT_PER_MIN` (default 20) per IP.

## 5. Specialists and tools

```mermaid
flowchart LR
    O[Orchestrator] --> N[nutrition]
    O --> F[fitness]
    O --> S[sleep_recovery]
    O --> M[mental_wellbeing]
    O --> C[checkin]
    N --> calc[calc_targets]
    N --> prof[get_profile]
    F --> prof
    F --> trend[trend_summary]
    S --> prof
    S --> trend
    M --> prof
    M --> trend
    C --> save[save_checkin]
    C --> trend
```

## 6. Data model

```mermaid
erDiagram
    PROFILE {
        int id PK "always 1 (single user)"
        text data "JSON: sex, age, weight_kg, height_cm, activity, goal, diet, injuries, notes"
    }
    CHECKIN {
        int id PK
        text day
        real weight_kg
        real sleep_hours
        int mood
        int stress
        int workout_done
        text notes
    }
    FEEDBACK {
        int id PK
        text ts
        text turn_id "Langfuse trace id when tracing is on"
        int rating "1 or -1"
    }
```

All data is local. `DELETE /api/data` wipes all three tables; `GET /api/export` dumps profile and check-ins.

## 7. API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health`, `/ready` | liveness; readiness (DB check) |
| POST | `/api/chat` | SSE stream of turn events |
| POST | `/api/targets` | TDEE, safe calorie target, macros, BMI |
| GET, PUT | `/api/profile` | read / save profile |
| GET, POST | `/api/checkins` | list / add check-in |
| POST | `/api/feedback` | thumbs up/down (also a Langfuse score) |
| GET | `/api/export` | export profile and check-ins |
| DELETE | `/api/data` | delete everything |

SSE events: `{type: "specialist", name}`, `{type: "safety", text, category}`,
`{type: "final", text, specialists, latency_ms, cost_usd, turn_id, output_gate_blocked}`, `{type: "error", text}`.

## 8. Deployment

`docker-compose.yml`: `backend` (volume `/data`, not published) and `frontend` (port 3000, `BACKEND_URL` baked in at
build time because Next rewrites are resolved during `next build`). Single backend worker: the rate limiter and the
SQLite store are per-process. Images are written but have not been built in CI yet.

## 9. Decisions and trade-offs

- **Agent SDK over a hand-rolled loop:** subagents, tool hooks and budgets come built in; cost is a bundled CLI and
  less control over the loop. Tool and hook behavior with the real CLI is still unverified (see CLAUDE.md).
- **Rules before an LLM for safety:** deterministic, instant, free, testable, but low recall on indirect phrasing.
  *Planned:* a Haiku-class classifier as a second stage (see evals hard tier).
- **SQLite and a single worker:** right for a local demo; a hosted multi-user version needs auth, per-user storage,
  a shared rate limiter and stronger privacy controls.
- **BYO key, no accounts:** zero server-side secrets for users; shifts cost and responsibility to the user.
