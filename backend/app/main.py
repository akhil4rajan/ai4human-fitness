import json
import os

from fastapi import FastAPI, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.memory.db import Store
from app.orchestrator import run_turn
from app.tools import calculators as calc

app = FastAPI(title="AI4Human")

DISCLAIMER = "Wellness guidance only; not medical advice."


class PlanRequest(BaseModel):
    sex: calc.Sex
    age: int = Field(ge=18, le=100)
    weight_kg: float = Field(gt=30, lt=300)
    height_cm: float = Field(gt=120, lt=250)
    activity: str
    goal: str = "maintain"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/targets")
def targets(req: PlanRequest) -> dict:
    t = calc.tdee(req.sex, req.weight_kg, req.height_cm, req.age, req.activity)
    kcal = calc.safe_calorie_target(req.sex, t, req.goal)  # type: ignore[arg-type]
    return {"tdee": round(t), "kcal": kcal, "macros": calc.macros(kcal, req.weight_kg, req.goal),
            "bmi": calc.bmi(req.weight_kg, req.height_cm), "disclaimer": DISCLAIMER}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store(os.environ.get("AI4HUMAN_DB", "ai4human.db"))
    return _store


@app.post("/api/chat")
async def chat(req: ChatRequest, x_anthropic_key: str | None = Header(default=None)) -> StreamingResponse:
    """SSE stream of orchestrator events. Safety gate runs first inside run_turn.
    The BYO API key is used for this request only and is never stored or logged."""

    async def events():
        async for ev in run_turn(req.message, get_store(), api_key=x_anthropic_key):
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
