"""Langfuse tracing for production monitoring: latency, cost, quality scores.

Everything here is a no-op unless LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set, so the
open-source demo runs without Langfuse. Health conversations are sensitive, so content is
REDACTED by default: only metadata (model, tokens, cost, timings, tool names) is exported.
Set LANGFUSE_CAPTURE_CONTENT=1 for local debugging only.
"""
import logging
import os
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

log = logging.getLogger("ai4human.observability")

# Span attributes that are safe to export when content capture is off (allow-list: anything new
# or unknown that an instrumentor adds is dropped rather than leaked).
_SAFE_PREFIXES = (
    "openinference.span.kind",
    "llm.model_name", "llm.provider", "llm.system", "llm.finish_reason",
    "llm.token_count", "llm.cost",
    "session.id", "agent.name", "tool.name", "tool.id",
    "langfuse.observation.type", "langfuse.observation.level", "langfuse.observation.status_message",
    "langfuse.observation.metadata", "langfuse.observation.model", "langfuse.observation.usage_details",
    "langfuse.observation.cost_details", "langfuse.trace.name", "langfuse.trace.tags",
    "langfuse.trace.metadata", "langfuse.session.id", "langfuse.environment", "langfuse.release",
    "langfuse.version", "gen_ai.request.model", "gen_ai.response.model", "gen_ai.usage",
)
_HEX32 = re.compile(r"^[0-9a-f]{32}$")


def _is_safe(key: str) -> bool:
    return key.startswith(_SAFE_PREFIXES)


def mask_otel_spans(*, params: Any) -> Any:
    """Export-stage masking: delete every non-allow-listed attribute (prompts, answers, tool I/O)."""
    from langfuse.types import MaskOtelSpansResult, OtelSpanPatch

    patches = {}
    for identifier, span in params.spans.items():
        doomed = tuple(k for k in span.attributes if not _is_safe(k))
        if doomed:
            patches[identifier] = OtelSpanPatch(
                delete_attributes=doomed, set_attributes={"app.content_redacted": True}
            )
    return MaskOtelSpansResult(span_patches=patches)


def mask_data(*, data: Any, **_: Any) -> str:
    """Langfuse-native input/output masking (we set none, but never let content through)."""
    return "[redacted]"


class TurnHandle:
    """Per-turn recorder. Safe to call when tracing is disabled."""

    def __init__(self, client: Any = None, span: Any = None) -> None:
        self._client, self._span = client, span
        self.trace_id: str | None = None
        if client is not None:
            try:
                self.trace_id = client.get_current_trace_id()
            except Exception:
                log.exception("could not read trace id")

    def _score(self, name: str, value: float, comment: str | None = None) -> None:
        if self._client is None:
            return
        try:
            self._client.score_current_trace(name=name, value=value, comment=comment, data_type="NUMERIC")
        except Exception:
            log.exception("score failed: %s", name)

    def observe(self, ev: Mapping[str, Any]) -> None:
        """Record a chat event. Never stores message text."""
        t = ev.get("type")
        meta: dict[str, Any] = {}
        if t == "safety":
            self._score("safety_gate_triggered", 1, comment=str(ev.get("category")))
            meta = {"safety_category": ev.get("category")}
        elif t == "final":
            lat, cost = ev.get("latency_ms"), ev.get("cost_usd")
            blocked = bool(ev.get("output_gate_blocked"))
            meta = {"specialists": ev.get("specialists", []), "latency_ms": lat, "cost_usd": cost}
            self._score("output_gate_blocked", 1.0 if blocked else 0.0)
            if lat is not None:
                self._score("latency_ms", float(lat))
            if cost is not None:
                self._score("cost_usd", float(cost))
            self._score("specialist_count", float(len(ev.get("specialists", []))))
        elif t == "error":
            meta = {"error": True}
        if meta and self._span is not None:
            try:
                self._span.update(metadata=meta, level="ERROR" if t == "error" else None)
            except Exception:
                log.exception("span update failed")


class Observability:
    def __init__(self, client: Any = None) -> None:
        self._client = client

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @contextmanager
    def turn(self, session_id: str | None) -> Iterator[TurnHandle]:
        if self._client is None:
            yield TurnHandle()
            return
        from langfuse import propagate_attributes

        env = os.environ.get("APP_ENV", "dev")
        with propagate_attributes(
            session_id=session_id, trace_name="chat_turn", tags=[f"env:{env}"],
            version=os.environ.get("APP_VERSION", "0.1.0"),
        ), self._client.start_as_current_observation(name="chat_turn", as_type="span") as span:
            yield TurnHandle(self._client, span)

    def score_feedback(self, trace_id: str | None, rating: int) -> bool:
        """Attach thumbs up/down to the turn's trace. Returns False if not applicable."""
        if self._client is None or not trace_id or not _HEX32.match(trace_id):
            return False
        try:
            self._client.create_score(trace_id=trace_id, name="user_feedback", value=float(rating),
                                      data_type="NUMERIC")
            return True
        except Exception:
            log.exception("feedback score failed")
            return False

    def shutdown(self) -> None:
        if self._client is not None:
            try:
                self._client.flush()
                self._client.shutdown()
            except Exception:
                log.exception("langfuse shutdown failed")


def init_observability(env: Mapping[str, str] | None = None) -> Observability:
    """Build the Langfuse client + instrument the Agent SDK, or return a disabled no-op."""
    env = os.environ if env is None else env
    if not (env.get("LANGFUSE_PUBLIC_KEY") and env.get("LANGFUSE_SECRET_KEY")):
        return Observability()
    try:
        from langfuse import Langfuse
        from openinference.instrumentation.claude_agent_sdk import ClaudeAgentSDKInstrumentor

        capture = env.get("LANGFUSE_CAPTURE_CONTENT") == "1"
        client = Langfuse(
            environment=env.get("APP_ENV", "dev"),
            release=env.get("APP_VERSION", "0.1.0"),
            mask=None if capture else mask_data,
            mask_otel_spans=None if capture else mask_otel_spans,
            sample_rate=float(env.get("LANGFUSE_SAMPLE_RATE", "1.0")),
        )
        if not client.auth_check():
            log.warning("Langfuse auth check failed; tracing disabled")
            return Observability()
        ClaudeAgentSDKInstrumentor().instrument()
        log.info("Langfuse tracing enabled (content capture %s)", "ON" if capture else "off")
        return Observability(client)
    except Exception:
        log.exception("Langfuse init failed; tracing disabled")
        return Observability()
