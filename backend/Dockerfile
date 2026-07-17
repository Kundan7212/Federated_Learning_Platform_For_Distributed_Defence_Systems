FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (from backend/requirements.txt)
# --timeout=300 : wait up to 5 min per chunk (avoids ReadTimeoutError on slow connections)
# --retries=10  : auto-retry on timeout
# cache mount   : pip wheel cache persists across builds and across folder moves.
#
# IMPORTANT — id=drdo-pip-cache:
#   Without an explicit id=, BuildKit derives the cache mount key from the
#   absolute path of the build context on disk. Moving the project folder
#   (e.g. V1 -> V2) would create a brand-new empty cache mount, forcing a
#   full re-download of torch (779MB) and all CUDA packages (~3-4GB total).
#   With id=drdo-pip-cache, ALL builds of this project — regardless of
#   folder name or location — share the same persistent pip wheel cache.

COPY backend/requirements.txt .
RUN --mount=type=cache,id=drdo-pip-cache,target=/root/.cache/pip \
    pip install \
    --timeout=300 \
    --retries=10 \
    -r requirements.txt

COPY backend/app ./app

COPY fl_engine  ./fl_engine
COPY privacy    ./privacy
COPY attacks    ./attacks
COPY defense    ./defense
COPY config     ./config

RUN mkdir -p /app/data /app/results

RUN useradd -m -u 1000 fluser && chown -R fluser:fluser /app
USER fluser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
