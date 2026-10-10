import asyncio
import json
import uuid

import pytest
from claude_agent_sdk import ResultMessage

from app.chat_service import stream_turn
from app.memory.db import Store
from app.observability import Observability, init_observability, mask_otel_spans


def collect(gen):
    async def go():
        return [e async for e in gen]
    return asyncio.run(go())


def runner_returning(text, cost=0.01):
    async def runner(prompt, options):
        yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
                            num_turns=1, session_id="s", result=text, total_cost_usd=cost)
    return runner


# --- disabled by default
def test_init_without_keys_is_noop():
    obs = init_observability(env={})
    assert not obs.enabled
    with obs.turn("sess") as h:
        h.observe({"type": "final", "latency_ms": 1, "cost_usd": 0.0, "specialists": []})
    assert obs.score_feedback("a" * 32, 1) is False
    obs.shutdown()


def test_stream_turn_adds_turn_id_and_flags_gate():
    ev = collect(stream_turn("diet?", Store(":memory:"), Observability(), runner=runner_returning("Eat 800 calories per day.")))
    final = ev[-1]
    assert final["type"] == "final" and final["turn_id"] and final["output_gate_blocked"] is True


def test_safety_event_has_category_and_no_runner_call():
    ev = collect(stream_turn("I want to die", Store(":memory:"), Observability(), runner=runner_returning("x")))
    assert ev == [{"type": "safety", "text": ev[0]["text"], "category": "crisis"}]


def test_producer_failure_becomes_generic_error():
    async def boom(prompt, options):
        raise RuntimeError("sk-ant-secret")
        yield  # pragma: no cover

    ev = collect(stream_turn("hi", Store(":memory:"), Observability(), runner=boom))
    assert ev[-1]["type"] == "error" and "secret" not in json.dumps(ev)


# --- real Langfuse client, in-memory exporter (no network)
@pytest.fixture
def lf():
    from langfuse import Langfuse
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    client = Langfuse(public_key=f"pk-lf-test-{uuid.uuid4().hex}", secret_key="sk-lf-test", base_url="http://127.0.0.1:9",
                      span_exporter=exporter, mask_otel_spans=mask_otel_spans, flush_at=1, tracing_enabled=True)
    scores = []
    client.score_current_trace = lambda **kw: scores.append(kw)  # avoid network
    client.create_score = lambda **kw: scores.append(kw)
    yield client, exporter, scores
    client.shutdown()


def test_turn_trace_records_metadata_and_scores_but_no_text(lf):
    client, exporter, scores = lf
    obs = Observability(client)
    secret = "my knee hurts and I weigh 82kg"
    ev = collect(stream_turn(secret, Store(":memory:"), obs, session_id="sess-1",
                             runner=runner_returning("Try low-impact cardio.", cost=0.02)))
    client.flush()
    final = ev[-1]
    assert final["turn_id"] and len(final["turn_id"]) == 32  # real Langfuse trace id
    names = {s["name"] for s in scores}
    assert {"output_gate_blocked", "latency_ms", "cost_usd", "specialist_count"} <= names
    spans = exporter.get_finished_spans()
    assert any(s.name == "chat_turn" for s in spans)
    blob = json.dumps([{k: str(v) for k, v in dict(s.attributes).items()} for s in spans])
    assert secret not in blob and "low-impact" not in blob


def test_safety_turn_scores_category_without_content(lf):
    client, exporter, scores = lf
    collect(stream_turn("I want to kill myself", Store(":memory:"), Observability(client), runner=runner_returning("x")))
    client.flush()
    hit = [s for s in scores if s["name"] == "safety_gate_triggered"]
    assert hit and hit[0]["comment"] == "crisis"
    assert "kill myself" not in json.dumps([dict(s.attributes) for s in exporter.get_finished_spans()], default=str)


def test_feedback_only_for_valid_trace_ids(lf):
    client, _, scores = lf
    obs = Observability(client)
    assert obs.score_feedback("not-a-trace", 1) is False
    assert obs.score_feedback("a" * 32, -1) is True
    assert scores[-1]["name"] == "user_feedback" and scores[-1]["value"] == -1.0


# --- mask function in isolation
def test_mask_deletes_content_keeps_metadata():
    from langfuse.types import MaskOtelSpansParams, OtelSpanData

    span = OtelSpanData(
        trace_id="1" * 32, span_id="2" * 16, parent_span_id=None, name="ClaudeAgentSDK.query",
        instrumentation_scope_name="openinference.instrumentation.claude_agent_sdk", instrumentation_scope_version="0",
        attributes={"input.value": "my diagnosis", "output.value": "answer", "llm.output_messages.0.message.content": "x",
                    "tool.parameters": "{}", "llm.token_count.total": 10, "llm.model_name": "m",
                    "openinference.span.kind": "AGENT", "some.future.attr": "leak?"},
        resource_attributes={},
    )
    res = mask_otel_spans(params=MaskOtelSpansParams(spans={("t", "s"): span}))
    patch = res.span_patches[("t", "s")]
    assert set(patch.delete_attributes) == {"input.value", "output.value", "llm.output_messages.0.message.content",
                                            "tool.parameters", "some.future.attr"}
