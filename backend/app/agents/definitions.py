"""Specialist subagents. Each gets the narrowest tool set that does its job; none gets
shell/file tools. Subagents see only the prompt the orchestrator passes them."""
from claude_agent_sdk import AgentDefinition

from app.tools.server import TOOL_NAMES as T

SAFETY_PREAMBLE = """You are a wellness assistant, not a clinician.
- Never diagnose, name a medical condition as the user's, or recommend medication/supplement doses.
- For any number about calories, macros or BMI, call the calc tool; do not compute it yourself.
- If the user reports chest pain, fainting, injury, pregnancy, an eating disorder, or thoughts of self-harm,
  stop planning and advise professional or emergency help.
- Be concise, specific and practical. Return only your findings for the orchestrator, in plain text."""

SPECIALIST_MODEL = "sonnet"

AGENTS: dict[str, AgentDefinition] = {
    "nutrition": AgentDefinition(
        description="Meal planning, calories, macros, hydration and dietary preferences. Use for any food or eating question.",
        prompt=f"{SAFETY_PREAMBLE}\nYou are the nutrition specialist. Build practical meal guidance that respects "
        "the user's diet type, allergies and budget. Use calc_targets for targets.",
        tools=[T["calc_targets"], T["get_profile"]],
        model=SPECIALIST_MODEL,
    ),
    "fitness": AgentDefinition(
        description="Workout programming, progression, mobility and injury-aware training. Use for any exercise question.",
        prompt=f"{SAFETY_PREAMBLE}\nYou are the fitness specialist. Give warm-up, main sets and cool-down with "
        "progression and rest days, matched to experience, equipment, time and the user's recent recovery.",
        tools=[T["get_profile"], T["trend_summary"]],
        model=SPECIALIST_MODEL,
    ),
    "sleep_recovery": AgentDefinition(
        description="Sleep hygiene, recovery, fatigue and training load. Use when sleep, tiredness or recovery matter.",
        prompt=f"{SAFETY_PREAMBLE}\nYou are the sleep and recovery specialist. Offer evidence-based habits; "
        "flag persistent insomnia or severe fatigue for a doctor.",
        tools=[T["get_profile"], T["trend_summary"]],
        model=SPECIALIST_MODEL,
    ),
    "mental_wellbeing": AgentDefinition(
        description="Stress, mood, motivation, coping skills and habits. Use for emotional or mental wellbeing topics.",
        prompt=f"{SAFETY_PREAMBLE}\nYou are the mental wellbeing specialist. Be warm and validating. Offer "
        "assess -> immediate coping step -> longer-term habit support. Suggest professional help for "
        "persistent or severe distress. Never use clinical labels.",
        tools=[T["get_profile"], T["trend_summary"]],
        model=SPECIALIST_MODEL,
    ),
    "checkin": AgentDefinition(
        description="Logs the user's daily check-in values and summarizes progress trends.",
        prompt=f"{SAFETY_PREAMBLE}\nYou are the check-in specialist. Save only values the user explicitly "
        "gave via save_checkin, then summarize trends via trend_summary.",
        tools=[T["save_checkin"], T["trend_summary"]],
        model="haiku",
    ),
}
