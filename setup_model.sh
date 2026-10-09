#!/bin/bash
# N-ATLAS Kit - download N-ATLaS (Q4_K_M GGUF) into LM Studio and start the local API server
set -e
cd "$(dirname "$0")"
set -a; source .env; set +a
REPO="QuantFactory/N-ATLaS-GGUF"
FILE=$(curl -s -H "Authorization: Bearer $HF_TOKEN" "https://huggingface.co/api/models/$REPO" | python3 -c "import sys,json;fs=[s['rfilename'] for s in json.load(sys.stdin)['siblings']];print([f for f in fs if 'Q4_K_M' in f and f.endswith('.gguf')][0])")
DEST="$HOME/.lmstudio/models/$REPO"
mkdir -p "$DEST"
echo "Downloading $FILE (~5 GB) ..."
curl -L -C - --progress-bar -H "Authorization: Bearer $HF_TOKEN" -o "$DEST/$FILE" "https://huggingface.co/$REPO/resolve/main/$FILE"
LMS="$HOME/.lmstudio/bin/lms"
echo "Starting LM Studio server ..."
"$LMS" server start --port 1234 || true
"$LMS" load "$DEST/$FILE" --identifier n-atlas --context-length 4096 -y || "$LMS" load n-atlas -y || true
echo "Testing ..."
curl -s http://localhost:1234/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"n-atlas","messages":[{"role":"user","content":"Translate to Yoruba: Good morning, how are you?"}],"max_tokens":60}' | python3 -c "import sys,json;print('N-ATLAS says:',json.load(sys.stdin)['choices'][0]['message']['content'])" | tee model_test.txt
echo "ALL DONE"
