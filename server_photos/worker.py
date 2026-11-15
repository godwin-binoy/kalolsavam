"""Photo Worker: Polls Core for jobs, processes images, uploads back."""
import os
import time
import requests
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("photo_worker")

CORE_URL = os.getenv("CORE_URL", "https://api.yourdomain.com")
SECRET_KEY = os.getenv("SECRET_KEY", "")

def run():
    log.info(f"Photo Worker starting. Polling {CORE_URL}...")
    while True:
        try:
            # 1. Poll Core for a job
            r = requests.post(f"{CORE_URL}/api/v1/photos/internal/queue/pull", headers={"Authorization": f"Bearer {SECRET_KEY}"}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("batch"):
                    batch = data["batch"]
                    log.info(f"Picked up Batch #{batch['id']} ({len(data['assets'])} files)")
                    
                    # 2. Download, process, and upload (Mock logic)
                    for asset in data["assets"]:
                        file_url = f"{CORE_URL}/api/v1/photos/assets/{asset['id']}/view"
                        log.info(f"Processing {asset['filename']}...")
                        # (Actual image processing logic here)
                    
                    # 3. Mark as complete
                    requests.post(f"{CORE_URL}/api/v1/photos/batches/{batch['id']}/publish", headers={"Authorization": f"Bearer {SECRET_KEY}"})
                    log.info(f"Batch #{batch['id']} published.")
        except Exception as e:
            log.error(f"Worker error: {e}")
        
        time.sleep(5)

if __name__ == "__main__":
    run()
