#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "▶ ngrok を起動中..."
ngrok http 8000 --log=stdout > /tmp/ngrok_ace.log 2>&1 &
NGROK_PID=$!

# ngrok の URL が出るまで待つ
echo "   URL 取得中..."
for i in $(seq 1 20); do
  NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null \
    | python3 -c "import sys,json; t=json.load(sys.stdin)['tunnels']; print([x['public_url'] for x in t if x['proto']=='https'][0])" 2>/dev/null || true)
  if [ -n "$NGROK_URL" ]; then
    break
  fi
  sleep 1
done

if [ -z "$NGROK_URL" ]; then
  echo "❌ ngrok URL の取得に失敗しました。ngrok のログ:"
  cat /tmp/ngrok_ace.log
  kill $NGROK_PID 2>/dev/null || true
  exit 1
fi

echo "✅ ngrok URL: $NGROK_URL"
echo ""

echo "▶ React をビルド中 (REACT_APP_API_URL=$NGROK_URL)..."
cd frontend
REACT_APP_API_URL="$NGROK_URL" npm run build --silent
cd ..
echo "✅ ビルド完了"
echo ""

echo "▶ FastAPI バックエンドを起動中..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  スマホでアクセス → $NGROK_URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

set -a && source .env 2>/dev/null || true && set +a
source .venv/bin/activate 2>/dev/null || true
uvicorn backend.main:app --host 0.0.0.0 --port 8000
