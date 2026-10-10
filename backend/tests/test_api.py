import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
PROFILE = {"sex": "female", "age": 30, "weight_kg": 60, "height_cm": 165, "activity": "light", "goal": "lose"}


def events(text):
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


def test_profile_roundtrip_and_validation():
    assert client.get("/api/profile").json() == {}
    assert client.put("/api/profile", json={**PROFILE, "diet": "vegetarian"}).status_code == 200
    assert client.get("/api/profile").json()["diet"] == "vegetarian"
    assert client.put("/api/profile", json={**PROFILE, "age": 15}).status_code == 422
    assert client.put("/api/profile", json={**PROFILE, "activity": "extreme"}).status_code == 422


def test_targets_rejects_bad_activity_instead_of_500():
    assert client.post("/api/targets", json={**PROFILE, "activity": "nope"}).status_code == 422


def test_checkins_and_export_and_delete():
    assert client.post("/api/checkins", json={"sleep_hours": 6.5, "mood": 7, "workout_done": True}).status_code == 201
    assert client.post("/api/checkins", json={"mood": 11}).status_code == 422
    assert len(client.get("/api/checkins").json()) == 1
    client.put("/api/profile", json=PROFILE)
    dump = client.get("/api/export").json()
    assert dump["profile"]["age"] == 30 and len(dump["checkins"]) == 1
    assert client.delete("/api/data").json() == {"deleted": True}
    assert client.get("/api/profile").json() == {} and client.get("/api/checkins").json() == []


def test_feedback():
    assert client.post("/api/feedback", json={"rating": 1}).status_code == 201
    assert client.post("/api/feedback", json={"rating": 5}).status_code == 422


def test_chat_fake_runner_enriched_final(monkeypatch):
    monkeypatch.setenv("AI4HUMAN_FAKE_RUNNER", "1")
    ev = events(client.post("/api/chat", json={"message": "plan my week"}).text)
    assert [e["name"] for e in ev if e["type"] == "specialist"] == ["nutrition", "sleep_recovery"]
    final = ev[-1]
    assert final["type"] == "final" and final["specialists"] == ["nutrition", "sleep_recovery"]
    assert final["latency_ms"] >= 0 and final["cost_usd"] == 0.0
