"""Photo Worker (Device 2): polls Core outbound, strips EXIF, optimizes to WebP."""
from __future__ import annotations

import hashlib
import hmac
import io
import logging
import os
import signal
import sys
import time
from pathlib import Path

import httpx
from PIL import Image, ImageOps

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("photo_worker")

CORE_URL = os.getenv("CORE_URL", "http://backend:8000").rstrip("/")
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
POLL_SEC = max(2, int(os.getenv("POLL_INTERVAL_SEC", "5")))
MAX_DIM = max(512, int(os.getenv("PHOTO_MAX_DIM", "2048")))
ARCHIVE_ORIGINALS = os.getenv("ARCHIVE_ORIGINALS", "false").lower() in ("1", "true", "yes")
ARCHIVE_DIR = Path(os.getenv("ARCHIVE_DIR", "/app/archive"))

_RUNNING = True


def _stop(*_args) -> None:
    global _RUNNING
    _RUNNING = False


def _worker_token(secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), b"worker:photos", hashlib.sha256).hexdigest()


def _optimize_webp(raw_bytes: bytes) -> bytes:
    with Image.open(io.BytesIO(raw_bytes)) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
        im.thumbnail((MAX_DIM, MAX_DIM), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        im.save(out, format="WEBP", quality=85, method=4)
        return out.getvalue()


def run() -> None:
    if len(SECRET_KEY) < 32:
        log.error("SECRET_KEY missing or shorter than 32 characters.")
        sys.exit(2)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    headers = {"X-Worker-Token": _worker_token(SECRET_KEY)}
    if ARCHIVE_ORIGINALS:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Photo Worker starting (CORE_URL=%s)", CORE_URL)
    backoff = POLL_SEC

    with httpx.Client(base_url=CORE_URL, headers=headers, timeout=30.0) as client:
        while _RUNNING:
            try:
                r = client.post("/api/v1/photos/internal/jobs/pull")
                r.raise_for_status()
                job = r.json().get("job")
                if not job:
                    backoff = POLL_SEC
                    time.sleep(POLL_SEC)
                    continue

                aid = job["id"]
                raw_resp = client.get(f"/api/v1/photos/internal/assets/{aid}/raw", timeout=60.0)
                raw_resp.raise_for_status()
                raw_bytes = raw_resp.content

                if ARCHIVE_ORIGINALS:
                    bdir = ARCHIVE_DIR / f"batch-{job['batch_id']}"
                    bdir.mkdir(parents=True, exist_ok=True)
                    (bdir / Path(job["filename"]).name).write_bytes(raw_bytes)

                webp_bytes = _optimize_webp(raw_bytes)
                comp = client.post(
                    f"/api/v1/photos/internal/jobs/{aid}/complete",
                    files={"file": (f"{aid}.webp", webp_bytes, "image/webp")},
                    timeout=60.0,
                )
                comp.raise_for_status()
                log.info("Processed asset #%s (%dB -> %dB)", aid, len(raw_bytes), len(webp_bytes))
                backoff = POLL_SEC
            except Exception as exc:
                log.warning("Worker cycle failed: %s", exc)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    run()
