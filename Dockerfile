# syntax=docker/dockerfile:1
# ============================================================================
# Kalolsavam — unified production image
# Stage 1: build the Astro site  |  Stage 2: Python backend + built dist
# ============================================================================

# ---------- Stage 1: Astro frontend ----------
FROM node:22-alpine AS frontend

WORKDIR /frontend

COPY package.json ./
COPY astro.config.mjs tsconfig.json ./
RUN npm install --no-audit --no-fund

COPY src ./src
COPY public ./public
COPY scripts ./scripts

# Same-origin by default: the backend serves the frontend and the API.
ARG PUBLIC_API_URL=same-origin
RUN echo "PUBLIC_API_URL=${PUBLIC_API_URL}" > .env

RUN npm run build

# ---------- Stage 2: Python backend ----------
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8000 \
    DB_PATH=/app/deployment/kalolsavam.db \
    DIST_PATH=/app/dist

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends sqlite3 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY alembic.ini ./
COPY server ./server
COPY --from=frontend /frontend/dist ./dist
COPY src/data/stages.json ./src/data/stages.json

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
 && mkdir -p /app/deployment \
 && touch /app/server/.env

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
