"""Vetted, static responses used when the safety gate fires. No LLM involved."""

RESPONSES = {
    "crisis": (
        "I'm really sorry you're going through this, and I'm glad you told me. You deserve "
        "support from a real person right now.\n\n"
        "- **In the US:** call or text **988** (Suicide & Crisis Lifeline), or call **911** if you "
        "are in immediate danger.\n"
        "- **Elsewhere:** find a local helpline at https://findahelpline.com\n\n"
        "If you can, reach out to someone you trust and stay with them. I'm an AI wellness "
        "companion, not a substitute for professional or emergency care."
    ),
    "medical": (
        "Those symptoms can be serious. Please contact a doctor or local emergency services "
        "now (911 in the US) rather than waiting. I can't assess medical symptoms, but I'm happy "
        "to help with your plan once you've been checked."
    ),
    "eating_disorder": (
        "Thank you for sharing that. What you describe may be a sign of an eating disorder, and "
        "support from a professional can help. In the US, the NEDA-affiliated resources at "
        "https://www.nationaleatingdisorders.org list helplines. I won't give calorie-restriction "
        "advice here, but I'm glad to talk about how you're feeling."
    ),
}
