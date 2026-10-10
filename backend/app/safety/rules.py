"""Fast, deterministic first-line safety rules. An LLM classifier can add recall on top,
but these rules alone must never miss the clear cases (crisis recall is the top metric)."""
import re
from dataclasses import dataclass

CRISIS = [
    r"\bkill (myself|my ?self)\b", r"\bsuicid", r"\bend (my life|it all)\b",
    r"\bwant to die\b", r"\bdon'?t want to (live|be alive)\b", r"\bbetter off (dead|without me)\b",
    r"\bself[- ]?harm", r"\bhurt(ing)? myself\b", r"\bcut(ting)? myself\b", r"\boverdos",
]
EATING_DISORDER = [
    r"\bpurg(e|ing)\b", r"\bstarv(e|ing) myself\b", r"\bmake myself (throw up|vomit)\b",
    r"\banorexi", r"\bbulimi", r"\bdon'?t (let myself )?eat\b.*\bdays\b",
]
MEDICAL_RED_FLAG = [
    r"\bchest pain\b", r"\bcan'?t breathe\b", r"\bfaint(ed|ing)\b", r"\bnumb(ness)? (in|on) (my )?(arm|face)\b",
    r"\bseizure\b", r"\bblood in (my )?(stool|urine)\b",
]


@dataclass(frozen=True)
class SafetyResult:
    category: str | None  # "crisis" | "eating_disorder" | "medical" | None

    @property
    def blocked(self) -> bool:
        return self.category is not None


def _any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def classify(text: str) -> SafetyResult:
    # Order = severity.
    if _any(CRISIS, text):
        return SafetyResult("crisis")
    if _any(MEDICAL_RED_FLAG, text):
        return SafetyResult("medical")
    if _any(EATING_DISORDER, text):
        return SafetyResult("eating_disorder")
    return SafetyResult(None)
