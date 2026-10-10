"""Deterministic stand-in for the Agent SDK, used only when AI4HUMAN_FAKE_RUNNER=1
(frontend smoke tests, demos without an API key)."""
from claude_agent_sdk import AssistantMessage, ResultMessage, ToolUseBlock


async def fake_query(prompt, options):
    for i, name in enumerate(("nutrition", "sleep_recovery")):
        yield AssistantMessage(
            content=[ToolUseBlock(id=str(i), name="Agent", input={"subagent_type": name})], model="fake"
        )
    yield ResultMessage(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=1,
        session_id="fake", result=f"(demo mode) You asked: {prompt[:200]}", total_cost_usd=0.0,
    )
