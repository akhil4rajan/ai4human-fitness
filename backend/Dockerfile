FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 AI4HUMAN_DB=/data/ai4human.db
WORKDIR /app

# The Claude Agent SDK wheel bundles the Claude Code CLI it drives, so no Node is needed here.
COPY pyproject.toml ./
COPY app ./app
RUN pip install ".[observability]" \
 && useradd --create-home --uid 10001 app \
 && mkdir /data && chown app /data

USER app
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/ready').status==200 else 1)"

# Single worker: rate limiting and the SQLite store are per-process.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
