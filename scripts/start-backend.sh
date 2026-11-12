#!/usr/bin/env bash
set -e

# ── Configuration ──────────────────────────────────────────────────────────
TUNNEL_NAME="kalolsavam-api"
PORT=8000
# ───────────────────────────────────────────────────────────────────────────

echo "🚀 Starting Kalolsavam Backend..."

# 1. Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ Error: cloudflared is not installed."
    echo "Please install it first (https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)"
    exit 1
fi

# 2. Start the Cloudflare Tunnel in the background
echo "🌐 Starting Cloudflare Tunnel ($TUNNEL_NAME)..."
cloudflared tunnel run "$TUNNEL_NAME" &
TUNNEL_PID=$!

# 3. Ensure the tunnel is killed when this script exits (Ctrl+C)
trap "echo '🛑 Stopping tunnel...'; kill $TUNNEL_PID" EXIT

# 4. Start the FastAPI backend
echo "⚙️ Starting FastAPI on port $PORT..."
# Using --reload for local development (auto-restarts on file changes)
python3 -m uvicorn server.app:app --host 127.0.0.1 --port $PORT --reload
