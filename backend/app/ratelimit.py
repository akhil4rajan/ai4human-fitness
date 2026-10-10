"""Small in-memory sliding-window limiter (single process; use a shared store if you scale out)."""
import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, limit: int, window_s: float = 60.0) -> None:
        self.limit, self.window = limit, window_s
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, now: float | None = None) -> float | None:
        """Return None if allowed, else seconds until the next slot frees up."""
        now = time.monotonic() if now is None else now
        q = self.hits[key]
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            return self.window - (now - q[0])
        q.append(now)
        return None


def client_ip(request: Request) -> str:
    if os.environ.get("TRUST_PROXY") == "1":
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def limit_dependency(limiter: RateLimiter):
    async def dep(request: Request) -> None:
        wait = limiter.check(client_ip(request))
        if wait is not None:
            raise HTTPException(429, "Too many requests. Please slow down.",
                                headers={"Retry-After": str(int(wait) + 1)})
    return dep
