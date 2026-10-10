# Security Policy

## Reporting a vulnerability
Please report security issues privately via GitHub's "Report a vulnerability" (Security tab of this repository)
rather than a public issue. Include steps to reproduce and the affected version/commit. For a safety failure
(harmful answer, missed crisis message) see `docs/safety.md`; do not include real personal health data.

## Handling of secrets and data
- Users' Anthropic API keys are supplied per request in the `X-Anthropic-Key` header, held in browser
  `sessionStorage`, and never stored or logged by the server.
- Profile and check-ins live in a local SQLite file. There are no accounts.
- Langfuse tracing is opt-in and redacts prompt, answer and tool content by default.
- Never commit `.env`, keys, or database files (`.gitignore` covers `.env` and `*.db`).

## Known security-relevant limitations
- No authentication: run on localhost or behind your own access control. The API is not hardened for public exposure.
- Rate limiting is in-memory and per process. Set `TRUST_PROXY=1` only behind a trusted reverse proxy.
- The model can be influenced by user-supplied text (prompt injection); code-level controls limit tools and outputs
  but are not a complete defense. See `docs/safety.md`.
