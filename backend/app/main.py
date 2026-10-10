from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.safety.gate import check_input
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
    message: str


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    # Safety gate runs before any agent. Orchestrator wiring lands in Phase 3.
    if (blocked := check_input(req.message)) is not None:
        return {"reply": blocked, "safety": True}
    return {"reply": "Orchestrator not wired yet.", "safety": False}
