# Multi-stage build: deps resolve in a cacheable layer, runtime image stays small
# and runs as a non-root user. TLS is terminated by the platform.
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN pip install uv
COPY pyproject.toml README.md ./
# Resolve and install runtime deps into a relocatable venv (not the local package).
RUN uv venv /opt/venv && . /opt/venv/bin/activate && uv pip install -r pyproject.toml

FROM python:3.12-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
# Ship only the shared kernel + the API service (tracing now lives in core/).
COPY core ./core
COPY backend ./backend
USER appuser
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
