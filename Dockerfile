FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server ./server
COPY deployment ./deployment
COPY public/admin ./public/admin
COPY public/stagemaster ./public/stagemaster

EXPOSE 8000

CMD ["python", "-m", "server"]
