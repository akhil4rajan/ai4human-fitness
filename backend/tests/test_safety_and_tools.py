import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.safety.rules import classify
from app.tools import calculators as calc

client = TestClient(app)


@pytest.mark.parametrize("msg", [
    "I want to kill myself", "i don't want to be alive anymore", "thinking about suicide",
    "I've been cutting myself", "everyone would be better off dead",
])
def test_crisis_recall(msg):
    assert classify(msg).category == "crisis"


@pytest.mark.parametrize("msg", ["Plan me a leg day", "I killed my workout today", "How much protein?"])
def test_no_false_positive(msg):
    assert not classify(msg).blocked


def test_medical_and_ed():
    assert classify("I get chest pain when I run").category == "medical"
    assert classify("I make myself throw up after meals").category == "eating_disorder"


def test_calorie_floor():
    assert calc.safe_calorie_target("female", 1300, "lose") == 1200


def test_tdee_known_value():
    assert round(calc.bmr_mifflin("male", 80, 180, 30)) == 1780


def test_chat_crisis_bypasses_agents():
    r = client.post("/api/chat", json={"message": "I want to die"})
    assert '"type": "safety"' in r.text and "988" in r.text


def test_targets_endpoint():
    r = client.post("/api/targets", json={"sex": "female", "age": 30, "weight_kg": 60,
                    "height_cm": 165, "activity": "light", "goal": "lose"}).json()
    assert r["kcal"] >= 1200
