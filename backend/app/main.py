import json
import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.chat_service import stream_turn
from app.fake_runner import fake_query
from app.logging_setup import RequestContextMiddleware, setup_logging
from app.memory.db import Store
from app.observability import Observability, init_observability
from app.ratelimit import RateLimiter, limit_dependency
from app.tools import calculators as calc

obs: Observability = Observability()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global obs
    obs = init_observability()
    yield
    obs.shutdown()


setup_logging(os.environ.get("LOG_LEVEL", "INFO"))
app = FastAPI(title="AI4Human", lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
chat_limiter = RateLimiter(int(os.environ.get("CHAT_RATE_LIMIT_PER_MIN", "20")))

DISCLAIMER = "Wellness guidance only; not medical advice."


Activity = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["lose", "maintain", "gain"]


class PlanRequest(BaseModel):
    sex: calc.Sex
    age: int = Field(ge=18, le=100)
    weight_kg: float = Field(gt=30, lt=300)
    height_cm: float = Field(gt=120, lt=250)
    activity: Activity
    goal: Goal = "maintain"


class ProfileIn(PlanRequest):
    diet: str = Field(default="", max_length=200)
    injuries: str = Field(default="", max_length=500)
    notes: str = Field(default="", max_length=1000)


class CheckinIn(BaseModel):
    weight_kg: float | None = Field(default=None, gt=30, lt=300)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    mood: int | None = Field(default=None, ge=1, le=10)
    stress: int | None = Field(default=None, ge=1, le=10)
    workout_done: bool | None = None
    notes: str | None = Field(default=None, max_length=500)


class FeedbackIn(BaseModel):
    turn_id: str | None = Field(default=None, max_length=64)
    rating: Literal[-1, 1]


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    """Readiness: the database answers."""
    try:
        get_store().conn.execute("SELECT 1").fetchone()
    except Exception as e:
        raise HTTPException(503, "database unavailable") from e
    return {"status": "ready"}


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


@app.post("/api/chat", dependencies=[Depends(limit_dependency(chat_limiter))])
async def chat(
    req: ChatRequest,
    x_anthropic_key: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None, max_length=64),
) -> StreamingResponse:
    """SSE stream of orchestrator events. Safety gate runs first inside run_turn.
    The BYO API key is used for this request only and is never stored or logged."""

    async def events():
        runner = fake_query if os.environ.get("AI4HUMAN_FAKE_RUNNER") == "1" else None
        async for ev in stream_turn(req.message, get_store(), obs, api_key=x_anthropic_key,
                                    session_id=x_session_id, runner=runner):
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/api/profile")
def read_profile() -> dict:
    return get_store().get_profile()


@app.put("/api/profile")
def write_profile(profile: ProfileIn) -> dict:
    get_store().set_profile(profile.model_dump())
    return profile.model_dump()


@app.get("/api/checkins")
def read_checkins(days: int = 30) -> list[dict]:
    return get_store().recent_checkins(max(1, min(days, 365)))


@app.post("/api/checkins", status_code=201)
def write_checkin(c: CheckinIn) -> dict:
    fields = c.model_dump()
    if fields["workout_done"] is not None:
        fields["workout_done"] = int(fields["workout_done"])
    get_store().add_checkin(**fields)
    return {"saved": True}


@app.post("/api/feedback", status_code=201)
def feedback(f: FeedbackIn) -> dict:
    get_store().add_feedback(f.turn_id, f.rating)
    obs.score_feedback(f.turn_id, f.rating)
    return {"saved": True}


@app.get("/api/export")
def export() -> dict:
    return get_store().export_all()


@app.delete("/api/data")
def delete_data() -> dict:
    get_store().delete_all()
    return {"deleted": True}
