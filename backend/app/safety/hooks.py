"""Code-level guardrails: a tool allow-list hook and an output gate."""
import re
from typing import Any

from app.tools.server import TOOL_NAMES

ALLOWED_TOOLS = {"Agent", "Task", *TOOL_NAMES.values()}

DISCLAIMER = "\n\n_Wellness guidance only, not medical advice._"
CALORIE_FLOOR = 1200

_DAILY = re.compile(r"(daily|per day|a day|each day|target|total)", re.I)
_KCAL = re.compile(r"(\d{1,2},?\d{3}|\d{3,4})\s*(kcal|calories|cal)\b", re.I)
_DOSING = re.compile(r"\b(take|taking|dose of|dosage)\b[^.\n]{0,30}\b\d+(\.\d+)?\s?(mg|mcg|µg|iu|g)\b", re.I)
_DIAGNOSIS = re.compile(
    r"\byou (have|are suffering from|likely have|probably have)\s+(an? )?"
    r"(depress\w*|anxiety disorder|eating disorder|anorexi\w*|bulimi\w*|bipolar\w*|adhd|ptsd|diabet\w*)",
    re.I,
)
SAFE_FALLBACK = (
    "I can't give that specific advice. I can help with general wellness habits, but for diagnosis, "
    "medication or very low calorie targets please talk to a doctor or registered dietitian."
)


async def pre_tool_use(input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
    """Deny anything outside the allow-list (built-in shell/file tools, unknown MCP tools)."""
    name = input_data.get("tool_name", "")
    if name in ALLOWED_TOOLS:
        return {}
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": f"Tool {name!r} is not permitted in this application.",
    }}


def violates(text: str) -> bool:
    for sentence in re.split(r"(?<=[.!?\n])\s+", text):
        if _DAILY.search(sentence):
            for m in _KCAL.finditer(sentence):
                if int(m.group(1).replace(",", "")) < CALORIE_FLOOR:
                    return True
    return bool(_DOSING.search(text) or _DIAGNOSIS.search(text))


def enforce_output(text: str) -> str:
    return (SAFE_FALLBACK if violates(text) else text.rstrip()) + DISCLAIMER
