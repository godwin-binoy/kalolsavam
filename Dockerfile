# syntax=docker/dockerfile:1
# ============================================================================
# Kalolsavam — backend-only image (split deploy)
#
# Static frontend is built and served by Cloudflare Pages. This image runs
# ONLY the FastAPI backend. The Cloudflare Tunnel sidecar (docker-compose.yml,
# profile "tunnel") publishes it at a fixed public hostname.
#
# No Node, no Astro, no dist/. If you ever need a single-origin image for
# local Docker preview, run `npm run build` on the host and mount ./dist in
# via a compose override — do not reintroduce Node here.
# ============================================================================

FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8000 \
    DB_PATH=/app/deployment/kalolsavam.db

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends sqlite3 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY alembic.ini ./
COPY server ./server
COPY src/data/stages.json ./src/data/stages.json

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
 && mkdir -p /app/deployment

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
