"""Deterministic health calculators. The LLM calls these instead of doing math."""
from typing import Literal

Sex = Literal["male", "female"]
ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}
# Hard floors enforced in code, independent of any prompt.
CALORIE_FLOOR = {"male": 1500, "female": 1200}


def bmr_mifflin(sex: Sex, weight_kg: float, height_cm: float, age: int) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + (5 if sex == "male" else -161)


def tdee(sex: Sex, weight_kg: float, height_cm: float, age: int, activity: str) -> float:
    if activity not in ACTIVITY:
        raise ValueError(f"activity must be one of {sorted(ACTIVITY)}")
    return bmr_mifflin(sex, weight_kg, height_cm, age) * ACTIVITY[activity]


def safe_calorie_target(sex: Sex, tdee_kcal: float, goal: Literal["lose", "maintain", "gain"]) -> int:
    """Moderate deficit/surplus (~15%), clamped to a safety floor."""
    factor = {"lose": 0.85, "maintain": 1.0, "gain": 1.10}[goal]
    return round(max(tdee_kcal * factor, CALORIE_FLOOR[sex]))


def macros(kcal: int, weight_kg: float, goal: str = "maintain") -> dict[str, int]:
    protein_g = round(weight_kg * (2.0 if goal == "lose" else 1.6))
    fat_g = round(kcal * 0.25 / 9)
    carb_g = max(round((kcal - protein_g * 4 - fat_g * 9) / 4), 0)
    return {"protein_g": protein_g, "fat_g": fat_g, "carb_g": carb_g}


def bmi(weight_kg: float, height_cm: float) -> float:
    return round(weight_kg / (height_cm / 100) ** 2, 1)
