from app.safety import resources, rules


def check_input(text: str) -> str | None:
    """Return a vetted response if the message must bypass the agents, else None."""
    result = rules.classify(text)
    return resources.RESPONSES[result.category] if result.blocked else None
