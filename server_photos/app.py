import os
import jwt
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from .models import init_db

app = FastAPI(title="Kalolsavam Photos")
SECRET_KEY = os.getenv("SECRET_KEY", "")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

engine = init_db(os.getenv("PHOTOS_DB_PATH", "sqlite:///./photos.db"))

def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "unauthorized")
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception:
        raise HTTPException(401, "invalid_token")

@app.get("/healthz")
def health():
    return {"ok": True, "service": "photos"}

# --- Placeholders for Phase 3 ---
@app.get("/api/v1/photos/ping")
def ping(user=Depends(verify_token)):
    return {"ok": True, "user": user.get("sub")}
