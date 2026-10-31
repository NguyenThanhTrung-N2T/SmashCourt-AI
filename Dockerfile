# ─── Stage 1: Install dependencies ───────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install dependencies into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Remove compiled bytecode & cache to shrink layer
    find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyc" -delete && \
    find /opt/venv -type f -name "*.pyo" -delete

# ─── Stage 2: Production runner ───────────────────────────────────────────────
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only application code (no tests, docs, etc.)
COPY ./app ./app
RUN chown -R appuser:appgroup /app

# Phiên bản của image (Epic 6C, P6-33): CI truyền --build-arg GIT_SHA=<sha> BUILD_VERSION=<tag>; CD so nhãn revision với sha cần triển khai
ARG GIT_SHA=""
ARG BUILD_VERSION="local"
LABEL org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.source="https://github.com/NguyenThanhTrung-N2T/SmashCourt-AI" \
      org.opencontainers.image.title="smashcourt-ai"
ENV APP_REVISION="${GIT_SHA}" \
    APP_VERSION="${BUILD_VERSION}"

# Use non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
