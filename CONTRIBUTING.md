# Contributing

1. Read `CLAUDE.md` (rules and gotchas) and `docs/architecture.md`.
2. Backend: `cd backend && pip install -e ".[dev]" && pytest -q && ruff check . && python -m evals.run`.
3. Frontend: `cd frontend && npm ci && npm run typecheck && npm run lint && npm test && npm run build`.
4. **Verify in a fresh clone before pushing** (`git clone . /tmp/x`, then run CI steps there). Local runs hide ignored
   and generated files that CI does not have.
5. Safety-relevant changes (`backend/app/safety/`, `calculators.py`, agent prompts) must keep the offline evals green
   and add dataset rows for the behavior changed. Don't edit eval data just to make a case pass.
6. Never log or trace message content, profiles or keys.
7. Keep PRs focused; describe what you verified and what you could not (for example, live-model behavior).
