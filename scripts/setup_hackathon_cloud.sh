#!/bin/bash
# =============================================================
# NAOMI Hackathon — Cloud Shell 全自動セットアップスクリプト
# 使い方:
#   export GEMINI_API_KEY="..."
#   export PHOENIX_API_KEY="..."
#   bash scripts/setup_hackathon_cloud.sh
# 接続が切れても tmux で再接続可能:
#   tmux new-session -d -s naomi 'bash scripts/setup_hackathon_cloud.sh 2>&1 | tee /tmp/naomi_setup.log'
#   tmux attach -t naomi
# =============================================================
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT="naomi-rapid-agent"
LOCATION="us-central1"
BUCKET="gs://naomi-rapid-agent-agent-engine-staging"
SERVICE="naomi"
LOG="/tmp/naomi_setup.log"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  NAOMI Hackathon Cloud Setup${NC}"
echo -e "${GREEN}========================================${NC}"

# ── 必須環境変数チェック ──────────────────────────────────────
if [ -z "$GEMINI_API_KEY" ]; then
  echo -e "${RED}ERROR: GEMINI_API_KEY が設定されていません${NC}"
  echo "  export GEMINI_API_KEY=\"...\""
  exit 1
fi
if [ -z "$PHOENIX_API_KEY" ]; then
  echo -e "${RED}ERROR: PHOENIX_API_KEY が設定されていません${NC}"
  echo "  export PHOENIX_API_KEY=\"...\""
  exit 1
fi

echo -e "${GREEN}✓ 環境変数OK${NC}"

# ── Step 1: GCP 設定 ─────────────────────────────────────────
echo ""
echo -e "${YELLOW}[1/7] GCP プロジェクト設定...${NC}"
gcloud config set project $PROJECT
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  --quiet
echo -e "${GREEN}✓ GCPサービス有効化完了${NC}"

# ── Step 2: ステージングバケット ──────────────────────────────
echo ""
echo -e "${YELLOW}[2/7] ステージングバケット作成...${NC}"
gcloud storage buckets describe $BUCKET > /dev/null 2>&1 || \
  gcloud storage buckets create $BUCKET \
    --location=$LOCATION \
    --uniform-bucket-level-access
echo -e "${GREEN}✓ バケット準備完了${NC}"

# ── Step 3: Python 依存関係 ──────────────────────────────────
echo ""
echo -e "${YELLOW}[3/7] Python パッケージインストール (数分かかります)...${NC}"
pip install -r requirements.txt -q
echo -e "${GREEN}✓ パッケージインストール完了${NC}"

# ── Step 4: Agent Engine デプロイ ────────────────────────────
echo ""
echo -e "${YELLOW}[4/7] Agent Engine デプロイ中 (5〜15分かかります)...${NC}"
export GOOGLE_CLOUD_PROJECT=$PROJECT
export GCP_PROJECT=$PROJECT
export GOOGLE_CLOUD_LOCATION=$LOCATION
export GOOGLE_CLOUD_REGION=$LOCATION
export VERTEX_AI_STAGING_BUCKET=$BUCKET

AGENT_ENGINE_RESOURCE=$(python scripts/deploy_agent_engine.py 2>/tmp/agent_deploy_err.txt | head -1)

if [ -z "$AGENT_ENGINE_RESOURCE" ]; then
  echo -e "${RED}ERROR: Agent Engine デプロイ失敗${NC}"
  cat /tmp/agent_deploy_err.txt
  exit 1
fi

export NAOMI_AGENT_ENGINE_RESOURCE="$AGENT_ENGINE_RESOURCE"
echo "$AGENT_ENGINE_RESOURCE" > /tmp/agent_engine_resource.txt
echo -e "${GREEN}✓ Agent Engine デプロイ完了${NC}"
echo "  Resource: $AGENT_ENGINE_RESOURCE"

# ── Step 5: Arize MCP 設定 ───────────────────────────────────
echo ""
echo -e "${YELLOW}[5/7] Arize Phoenix MCP 設定...${NC}"
export ARIZE_MCP_COMMAND="npx"
export ARIZE_MCP_ARGS_JSON="[\"-y\",\"@arizeai/phoenix-mcp@latest\",\"--baseUrl\",\"https://app.phoenix.arize.com\",\"--apiKey\",\"$PHOENIX_API_KEY\"]"
export ENABLE_HACKATHON_INTEGRATIONS="true"

# ── Step 6: オンライン検証 ────────────────────────────────────
echo ""
echo -e "${YELLOW}[6/7] オンライン検証実行...${NC}"
python scripts/verify_hackathon_integrations.py --online

# ── Step 7: Cloud Run デプロイ ───────────────────────────────
echo ""
echo -e "${YELLOW}[7/7] Cloud Run デプロイ中...${NC}"

cat > /tmp/cloudrun.env.yaml << EOF
ENABLE_HACKATHON_INTEGRATIONS: "true"
GOOGLE_CLOUD_PROJECT: "${PROJECT}"
GCP_PROJECT: "${PROJECT}"
GOOGLE_CLOUD_LOCATION: "${LOCATION}"
GOOGLE_CLOUD_REGION: "${LOCATION}"
NAOMI_AGENT_ENGINE_RESOURCE: "${AGENT_ENGINE_RESOURCE}"
ARIZE_MCP_COMMAND: "npx"
ARIZE_MCP_ARGS_JSON: '["-y","@arizeai/phoenix-mcp@latest","--baseUrl","https://app.phoenix.arize.com","--apiKey","${PHOENIX_API_KEY}"]'
EOF

gcloud run deploy $SERVICE \
  --source . \
  --region $LOCATION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300 \
  --env-vars-file /tmp/cloudrun.env.yaml \
  --set-env-vars GEMINI_API_KEY="$GEMINI_API_KEY" \
  --quiet

CLOUD_RUN_URL=$(gcloud run services describe $SERVICE \
  --region $LOCATION \
  --format "value(status.url)")

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ セットアップ完了！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "  Agent Engine : $AGENT_ENGINE_RESOURCE"
echo "  Cloud Run URL: $CLOUD_RUN_URL"
echo ""
echo -e "${YELLOW}次のステップ:${NC}"
echo "  1. ブラウザで $CLOUD_RUN_URL を開く"
echo "  2. NAOMIに1回メッセージを送る"
echo "  3. debug expanderで以下を確認:"
echo "     Gemini: called"
echo "     Agent Engine: called"
echo "     Arize MCP: called"
echo "     Trace ID: present"
echo ""
rm -f /tmp/cloudrun.env.yaml
