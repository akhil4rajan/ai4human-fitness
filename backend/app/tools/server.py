"""In-process MCP server exposing deterministic tools to the agents.
Tool names seen by the model are mcp__health__<name>."""
import json
from typing import Any

from claude_agent_sdk import ToolAnnotations, create_sdk_mcp_server, tool

from app.memory.db import Store
from app.tools import calculators as calc

SERVER_NAME = "health"
READ_ONLY = ToolAnnotations(readOnlyHint=True)


def _ok(payload: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def _err(msg: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": msg}], "is_error": True}


def build_tools(store: Store) -> list:
    @tool(
        "calc_targets",
        "Compute TDEE, a safe daily calorie target (never below the safety floor), macros and BMI. "
        "Always use this for calorie/macro numbers; never calculate them yourself.",
        {
            "type": "object",
            "properties": {
                "sex": {"type": "string", "enum": ["male", "female"]},
                "age": {"type": "integer", "minimum": 18, "maximum": 100},
                "weight_kg": {"type": "number", "minimum": 30, "maximum": 300},
                "height_cm": {"type": "number", "minimum": 120, "maximum": 250},
                "activity": {"type": "string", "enum": sorted(calc.ACTIVITY)},
                "goal": {"type": "string", "enum": ["lose", "maintain", "gain"]},
            },
            "required": ["sex", "age", "weight_kg", "height_cm", "activity"],
        },
        annotations=READ_ONLY,
    )
    async def calc_targets(args: dict[str, Any]) -> dict[str, Any]:
        try:
            goal = args.get("goal", "maintain")
            t = calc.tdee(args["sex"], args["weight_kg"], args["height_cm"], args["age"], args["activity"])
            kcal = calc.safe_calorie_target(args["sex"], t, goal)
            return _ok({"tdee": round(t), "kcal": kcal, "macros": calc.macros(kcal, args["weight_kg"], goal),
                        "bmi": calc.bmi(args["weight_kg"], args["height_cm"])})
        except (KeyError, ValueError, TypeError) as e:
            return _err(f"Invalid input: {e}")

    @tool("get_profile", "Read the user's saved health profile and goals.", {"type": "object", "properties": {}},
          annotations=READ_ONLY)
    async def get_profile(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(store.get_profile())

    @tool(
        "save_checkin",
        "Record a daily check-in (only values the user actually reported).",
        {
            "type": "object",
            "properties": {
                "weight_kg": {"type": "number"},
                "sleep_hours": {"type": "number", "minimum": 0, "maximum": 24},
                "mood": {"type": "integer", "minimum": 1, "maximum": 10},
                "stress": {"type": "integer", "minimum": 1, "maximum": 10},
                "workout_done": {"type": "boolean"},
                "notes": {"type": "string"},
            },
        },
    )
    async def save_checkin(args: dict[str, Any]) -> dict[str, Any]:
        store.add_checkin(**{**args, "workout_done": int(args["workout_done"]) if "workout_done" in args else None})
        return _ok({"saved": True})

    @tool(
        "trend_summary",
        "Summarize recent check-ins: averages and direction for weight, sleep, mood, stress.",
        {"type": "object", "properties": {"days": {"type": "integer", "minimum": 3, "maximum": 60}}},
        annotations=READ_ONLY,
    )
    async def trend_summary(args: dict[str, Any]) -> dict[str, Any]:
        rows = store.recent_checkins(args.get("days", 14))
        out: dict[str, Any] = {"n": len(rows)}
        for k in ("weight_kg", "sleep_hours", "mood", "stress"):
            vals = [r[k] for r in rows if r[k] is not None]
            if vals:
                out[k] = {"avg": round(sum(vals) / len(vals), 1), "change": round(vals[-1] - vals[0], 1)}
        return _ok(out)

    return [calc_targets, get_profile, save_checkin, trend_summary]


TOOL_NAMES = {n: f"mcp__{SERVER_NAME}__{n}" for n in ("calc_targets", "get_profile", "save_checkin", "trend_summary")}


def build_server(store: Store):
    return create_sdk_mcp_server(name=SERVER_NAME, version="1.0.0", tools=build_tools(store))
