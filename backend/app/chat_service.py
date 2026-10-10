"""Runs one chat turn inside an observability trace, streaming events to the caller.

The trace lives entirely inside a producer task. Holding an OpenTelemetry context open across
a generator's yields can fail to detach (e.g. when the client disconnects), so we never do."""
import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from app.memory.db import Store
from app.observability import Observability
from app.orchestrator import run_turn

log = logging.getLogger("ai4human.chat")

LATENCY_ALERT_MS = 60_000
COST_ALERT_USD = 0.50


async def stream_turn(
    message: str,
    store: Store,
    obs: Observability,
    *,
    api_key: str | None = None,
    session_id: str | None = None,
    runner: Callable[..., AsyncIterator[Any]] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def produce() -> None:
        try:
            with obs.turn(session_id) as handle:
                async for ev in run_turn(message, store, api_key=api_key, runner=runner):
                    if ev["type"] == "final":
                        ev["turn_id"] = handle.trace_id or uuid.uuid4().hex
                        if (ev.get("latency_ms") or 0) > LATENCY_ALERT_MS or (ev.get("cost_usd") or 0) > COST_ALERT_USD:
                            log.warning("slow_or_expensive_turn", extra={"latency_ms": ev.get("latency_ms"),
                                                                         "cost_usd": ev.get("cost_usd")})
                    handle.observe(ev)
                    await queue.put(ev)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("chat turn failed")
            await queue.put({"type": "error", "text": "Something went wrong. Please try again."})
        finally:
            await queue.put(None)

    task = asyncio.create_task(produce())
    try:
        while (ev := await queue.get()) is not None:
            yield ev
    finally:
        task.cancel()
