# Observability with Langfuse

Tracing is **off** unless `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set. Install extras:
`pip install -e ".[observability]"` (already included in the Docker image).

## What is captured

- One trace per chat turn (`chat_turn`), grouped by an anonymous per-tab `session_id`; tagged `env:<APP_ENV>`.
- Via OpenInference instrumentation of the Claude Agent SDK: the agent run, each tool call, and subagent
  delegations as nested spans, with model name, token counts and cost.
- Scores on each trace: `latency_ms`, `cost_usd`, `specialist_count`, `output_gate_blocked` (0/1),
  `safety_gate_triggered` (comment = category; no message text), and `user_feedback` (±1 from the thumbs).
- Metadata: specialists consulted, safety category, error flag.

## Privacy

Prompts, answers and tool inputs/outputs are removed at export (`mask_otel_spans` allow-list in
`backend/app/observability.py`: unknown attributes are dropped, not leaked). `LANGFUSE_CAPTURE_CONTENT=1`
disables masking for local debugging; never use it with real users. Exception events can still carry text, and
masking only edits span attributes, so review a few real traces after enabling. Pick the Langfuse region (EU/US/
Japan/HIPAA) deliberately, and sample with `LANGFUSE_SAMPLE_RATE` if volume is a concern.

## Latency, cost and quality checks

- Dashboards: group by `session_id`, model, or the `latency_ms` / `cost_usd` scores; alert on p95 latency and
  p95 cost per turn. The app also logs a `slow_or_expensive_turn` warning above 60 s or $0.50.
- Hard limits stay in code: `max_turns=12`, `max_budget_usd=1.0` per turn, subagent depth 1, concurrency 4,
  chat rate limit per IP.
- Watch `output_gate_blocked` and `safety_gate_triggered` rates: a spike after a prompt or model change is a
  regression signal.

## Self-hosting

Langfuse Cloud's free tier is the simplest start. Self-hosting needs Postgres, ClickHouse, Redis and object
storage; follow Langfuse's own guide and point `LANGFUSE_BASE_URL` at it. It is intentionally not bundled here.
