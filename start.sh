#!/bin/bash
# Install the kit, check the model, run a quick demo
cd "$(dirname "$0")"
python3 -m pip install -q -e ".[server,demo,dev]" --break-system-packages 2>/dev/null || python3 -m pip install -q -e ".[server,demo,dev]"
python3 -m natlas_kit.cli doctor && \
python3 -m natlas_kit.cli translate "Where is the hospital?" --to ha && \
python3 -m natlas_kit.cli scam "Your BVN has been blocked, send your PIN to reactivate" && \
python3 -m natlas_kit.cli eval --out eval_results 2>&1 | tail -40 | tee first_eval.txt
