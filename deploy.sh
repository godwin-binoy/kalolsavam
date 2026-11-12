#!/usr/bin/env bash
set -e

# ── Configuration ──────────────────────────────────────────────────────────
# You can hardcode these, or export them in your terminal before running ./deploy.sh
# export CLOUDFLARE_API_TOKEN="your-api-token"
# export CLOUDFLARE_ACCOUNT_ID="your-account-id"

PROJECT_NAME="kalolsavam"

if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
  echo "❌ Error: CLOUDFLARE_API_TOKEN is not set."
  echo "Run: export CLOUDFLARE_API_TOKEN='your_token_here'"
  exit 1
fi

if [ -z "$CLOUDFLARE_ACCOUNT_ID" ]; then
  echo "❌ Error: CLOUDFLARE_ACCOUNT_ID is not set."
  echo "Run: export CLOUDFLARE_ACCOUNT_ID='your_account_id_here'"
  exit 1
fi

# ── Build ──────────────────────────────────────────────────────────────────
echo "📦 Building Astro site..."
npm run build

# ── Deploy ─────────────────────────────────────────────────────────────────
echo "🚀 Deploying to Cloudflare Pages (Project: $PROJECT_NAME)..."
npx wrangler pages deploy dist --project-name="$PROJECT_NAME"

echo "✅ Deployment complete!"
