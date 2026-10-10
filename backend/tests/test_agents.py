import asyncio
import json

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

from app.agents.definitions import AGENTS
from app.memory.db import Store
from app.orchestrator import build_options, run_turn
from app.safety import hooks
from app.tools.server import build_tools

FORBIDDEN = {"Bash", "Write", "Edit", "Read", "WebFetch", "WebSearch"}


def tools_by_name():
    return {t.name: t for t in build_tools(Store(":memory:"))}


def call(tool, args):
    return asyncio.run(tool.handler(args))


def collect(gen):
    async def go():
        return [e async for e in gen]
    return asyncio.run(go())


def fake_runner(*messages, raises=None):
    async def runner(prompt, options):
        assert prompt
        if raises:
            raise raises
        for m in messages:
            yield m
    return runner


def result(text, is_error=False):
    return ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=is_error,
                         num_turns=1, session_id="s", result=text)


# --- tools
def test_calc_targets_respects_floor():
    r = call(tools_by_name()["calc_targets"], {"sex": "female", "age": 60, "weight_kg": 45,
             "height_cm": 150, "activity": "sedentary", "goal": "lose"})
    assert json.loads(r["content"][0]["text"])["kcal"] >= 1200


def test_calc_targets_bad_input_is_error():
    assert call(tools_by_name()["calc_targets"], {"sex": "female"}).get("is_error")


def test_checkin_roundtrip():
    store = Store(":memory:")
    t = {x.name: x for x in build_tools(store)}
    call(t["save_checkin"], {"sleep_hours": 5, "stress": 8, "workout_done": False})
    call(t["save_checkin"], {"sleep_hours": 7, "stress": 4})
    out = json.loads(call(t["trend_summary"], {})["content"][0]["text"])
    assert out["n"] == 2 and out["sleep_hours"]["change"] == 2.0


# --- agents
def test_agents_are_locked_down():
    assert set(AGENTS) == {"nutrition", "fitness", "sleep_recovery", "mental_wellbeing", "checkin"}
    for name, a in AGENTS.items():
        assert a.tools and not FORBIDDEN & set(a.tools), name
        assert all(t.startswith("mcp__health__") for t in a.tools), name
        assert a.model, name
    assert "mcp__health__calc_targets" not in AGENTS["mental_wellbeing"].tools


def test_options_have_no_dangerous_tools():
    o = build_options({"age": 30}, Store(":memory:"), "sk-test")
    assert o.tools == ["Agent"] and o.setting_sources == [] and o.env["ANTHROPIC_API_KEY"] == "sk-test"
    assert not FORBIDDEN & set(o.allowed_tools)


# --- hook + output gate
def test_hook_denies_unknown_tools():
    deny = asyncio.run(hooks.pre_tool_use({"tool_name": "Bash"}, None, None))
    assert deny["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert asyncio.run(hooks.pre_tool_use({"tool_name": "Agent"}, None, None)) == {}


@pytest.mark.parametrize("bad", [
    "Your daily target is 900 calories.",
    "Aim for a total of 1,000 kcal per day.",
    "Take 500 mg of ashwagandha every night.",
    "You have depression.",
])
def test_output_gate_blocks(bad):
    assert hooks.violates(bad) and hooks.SAFE_FALLBACK in hooks.enforce_output(bad)


def test_output_gate_allows_normal():
    ok = "Daily target: 1,800 kcal. A 150 calorie snack is fine."
    assert not hooks.violates(ok) and ok in hooks.enforce_output(ok)


# --- orchestrator (fake runner, no network)
def test_crisis_never_reaches_runner():
    called = []

    async def runner(prompt, options):
        called.append(prompt)
        yield result("x")

    ev = collect(run_turn("I want to kill myself", Store(":memory:"), runner=runner))
    assert ev[0]["type"] == "safety" and "988" in ev[0]["text"] and not called


def test_specialist_events_and_final():
    msgs = [
        AssistantMessage(content=[ToolUseBlock(id="1", name="Agent", input={"subagent_type": "nutrition"}),
                                  ToolUseBlock(id="2", name="Agent", input={"subagent_type": "sleep_recovery"})],
                         model="m"),
        AssistantMessage(content=[TextBlock(text="draft")], model="m"),
        result("Plan: eat well."),
    ]
    ev = collect(run_turn("plan my week", Store(":memory:"), runner=fake_runner(*msgs)))
    assert [e["name"] for e in ev if e["type"] == "specialist"] == ["nutrition", "sleep_recovery"]
    assert ev[-1]["type"] == "final" and "Plan: eat well." in ev[-1]["text"]


def test_unsafe_model_output_is_replaced():
    ev = collect(run_turn("diet?", Store(":memory:"), runner=fake_runner(result("Eat 800 calories per day."))))
    assert hooks.SAFE_FALLBACK in ev[-1]["text"]


def test_runner_failure_is_generic_error():
    ev = collect(run_turn("hi", Store(":memory:"), runner=fake_runner(raises=RuntimeError("secret sk-ant-123"))))
    assert ev == [{"type": "error", "text": "Could not reach the model. Check your API key and try again."}]


def test_error_result():
    ev = collect(run_turn("hi", Store(":memory:"), runner=fake_runner(result("", is_error=True))))
    assert ev[-1]["type"] == "error"
