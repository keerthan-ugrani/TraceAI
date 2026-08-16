FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN pip install --no-cache-dir uv==0.12.5

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY data ./data
COPY app.py ./app.py

RUN uv sync --frozen --no-dev --extra ai

RUN addgroup --system traceai \
    && adduser --system --ingroup traceai traceai \
    && chown -R traceai:traceai /app

USER traceai

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD [".venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"]

CMD [".venv/bin/streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
