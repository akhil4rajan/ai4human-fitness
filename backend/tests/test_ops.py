import json
import logging

from fastapi.testclient import TestClient

from app import main
from app.logging_setup import JsonFormatter
from app.ratelimit import RateLimiter

client = TestClient(main.app)


def test_request_id_header_generated_and_echoed():
    r = client.get("/health")
    assert len(r.headers["x-request-id"]) >= 8
    assert client.get("/health", headers={"X-Request-ID": "abc123"}).headers["x-request-id"] == "abc123"


def test_ready_checks_db():
    assert client.get("/ready").json() == {"status": "ready"}


def test_rate_limiter_window():
    rl = RateLimiter(2, window_s=10)
    assert rl.check("ip", now=0) is None and rl.check("ip", now=1) is None
    wait = rl.check("ip", now=2)
    assert wait is not None and 7 < wait <= 8
    assert rl.check("other", now=2) is None
    assert rl.check("ip", now=10.5) is None  # oldest hit expired


def test_chat_returns_429_after_limit(monkeypatch):
    monkeypatch.setenv("AI4HUMAN_FAKE_RUNNER", "1")
    monkeypatch.setattr(main.chat_limiter, "limit", 2)
    main.chat_limiter.hits.clear()
    codes = [client.post("/api/chat", json={"message": "hi"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    r = client.post("/api/chat", json={"message": "hi"})
    assert r.headers["retry-after"]
    main.chat_limiter.hits.clear()


def test_logs_are_json_without_bodies(caplog):
    record = logging.LogRecord("t", logging.INFO, "f", 1, "request", None, None)
    record.status = 200
    out = json.loads(JsonFormatter().format(record))
    assert out["msg"] == "request" and out["status"] == 200 and "request_id" in out


def test_exception_text_not_logged():
    try:
        raise ValueError("sk-ant-secret and my diagnosis")
    except ValueError:
        import sys
        rec = logging.LogRecord("t", logging.ERROR, "f", 1, "boom", None, sys.exc_info())
    out = JsonFormatter().format(rec)
    assert "secret" not in out and "ValueError" in out
