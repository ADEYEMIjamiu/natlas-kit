#!/bin/bash
# Share N-ATLAS with beta testers: secure API gateway + Ṣọ́ra web app, via free Cloudflare tunnels.
# Keep this Terminal window open while testers are testing. Press Ctrl+C to stop sharing.
cd "$(dirname "$0")"
mkdir -p bin logs
touch .env
if ! grep -q '^NATLAS_GATEWAY_KEY=' .env; then
  echo "NATLAS_GATEWAY_KEY=natlas-$(LC_ALL=C tr -dc 'a-z0-9' </dev/urandom | head -c 10)" >> .env
fi
set -a; source .env; set +a

# 1. model
LMS="$HOME/.lmstudio/bin/lms"
"$LMS" server start --port 1234 >/dev/null 2>&1
"$LMS" ps 2>/dev/null | grep -qi n-atlas || "$LMS" load n-atlas --identifier n-atlas -y >/dev/null 2>&1 || "$LMS" load n-atlas -y >/dev/null 2>&1
curl -s localhost:1234/v1/models | grep -q n-atlas && echo "✅ N-ATLAS model running" || { echo "❌ Model not loaded. Open LM Studio, load N-ATLaS with identifier n-atlas, then rerun."; exit 1; }

# 2. cloudflared (free, no account needed)
if [ ! -x bin/cloudflared ]; then
  echo "Downloading cloudflared ..."
  curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz | tar -xz -C bin
  chmod +x bin/cloudflared
fi

# 3. start services
python3 -m pip install -q -e ".[server,demo]" >/dev/null 2>&1
pkill -f "natlas_kit.cli serve" 2>/dev/null; pkill -f "streamlit run apps/scam_checker" 2>/dev/null; pkill -f "bin/cloudflared" 2>/dev/null
sleep 1
NATLAS_GATEWAY_LOG="$PWD/gateway_log.csv" python3 -m natlas_kit.cli serve --port 8000 > logs/api.log 2>&1 &
NATLAS_PUBLIC=1 python3 -m streamlit run apps/scam_checker/app.py --server.port 8501 --server.headless true \
  --browser.gatherUsageStats false > logs/app.log 2>&1 &
sleep 4
bin/cloudflared tunnel --no-autoupdate --url http://localhost:8000 > logs/tunnel_api.log 2>&1 &
bin/cloudflared tunnel --no-autoupdate --url http://localhost:8501 > logs/tunnel_app.log 2>&1 &
echo "Opening tunnels (about 15 seconds) ..."
for i in $(seq 1 30); do
  API=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' logs/tunnel_api.log | head -1)
  APP=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' logs/tunnel_app.log | head -1)
  [ -n "$API" ] && [ -n "$APP" ] && break; sleep 1
done
cat > SHARE_LINKS.txt <<TXT
=== N-ATLAS Kit beta-test links (valid while this Terminal stays open) ===

FOR DEVELOPERS (Colab notebook):
  Notebook : https://colab.research.google.com/github/ADEYEMIjamiu/natlas-kit/blob/main/notebooks/NATLAS_Kit_Beta_Test.ipynb
  Endpoint : $API/v1
  API key  : $NATLAS_GATEWAY_KEY

FOR EVERYONE (Ṣọ́ra scam checker, no coding):
  $APP

Usage evidence is logged to: gateway_log.csv and apps/scam_checker/session_log.csv
TXT
cat SHARE_LINKS.txt
echo; echo "🟢 Sharing is ON. Keep this window open and your Mac awake (Ctrl+C to stop)."
caffeinate -dimsu -w $$ &
trap 'pkill -f "natlas_kit.cli serve"; pkill -f "streamlit run apps/scam_checker"; pkill -f "bin/cloudflared"; echo "Sharing stopped."; exit 0' INT TERM
wait
