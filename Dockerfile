FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./alembic.ini
COPY server ./server
COPY public/assets ./public/assets
COPY public/admin ./public/admin
COPY public/stagemaster ./public/stagemaster
COPY public/dashboard ./public/dashboard
COPY public/manifest.json ./public/manifest.json
COPY public/robots.txt ./public/robots.txt
COPY src/data/stages.json ./src/data/stages.json

RUN mkdir -p /app/deployment

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

CMD ["python", "-m", "server"]
