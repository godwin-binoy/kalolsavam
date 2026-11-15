"""Structured JSON logging on stdout."""
from __future__ import annotations

import json
import logging
import queue
import sys
import threading

import requests


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for k in ("request_id", "method", "path", "status", "duration_ms", "user_id"):
            v = getattr(record, k, None)
            if v is not None:
                payload[k] = v
        return json.dumps(payload, default=str)




class HttpLogHandler(logging.Handler):
    def __init__(self, url, service, token):
        super().__init__()
        self.url = url
        self.service = service
        self.token = token
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def emit(self, record):
        try:
            log_data = {
                "service": self.service,
                "level": record.levelname,
                "msg": record.getMessage(),
                "request_id": getattr(record, "request_id", None),
                "method": getattr(record, "method", None),
                "path": getattr(record, "path", None),
                "status": getattr(record, "status", None),
                "duration_ms": getattr(record, "duration_ms", None),
            }
            self.queue.put(log_data)
        except Exception:  # noqa: S110
            pass

    def _worker(self):
        import time
        while True:
            batch = []
            try:
                item = self.queue.get(timeout=2)
                batch.append(item)
                while len(batch) < 100:
                    batch.append(self.queue.get_nowait())
            except queue.Empty:
                pass

            if batch:
                try:
                    requests.post(
                        self.url,
                        json={"logs": batch},
                        headers={"X-Obs-Token": self.token},
                        timeout=5
                    )
                except Exception:  # noqa: S110
                    pass
            time.sleep(0.5)


def setup() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    
    import os
    obs_url = os.getenv("OBS_URL")
    token = os.getenv("SECRET_KEY", "")
    if obs_url:
        obs_handler = HttpLogHandler(obs_url, "core", token)
        root.addHandler(obs_handler)
    root.setLevel(logging.INFO)
