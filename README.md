# N-ATLAS Kit 🇳🇬

**Developer toolkit for [N-ATLAS](https://huggingface.co/NCAIR1/N-ATLaS), Nigeria's multilingual LLM (Yoruba, Hausa, Igbo, Nigerian English).**
Built for the National AI Innovation Challenge (NAIC), Problem Statement 1: Developer Infrastructure.

N-ATLAS is open, but turning it into a product still takes a lot of glue code. N-ATLAS Kit gives Nigerian developers:

| Component | What it does |
|---|---|
| **Python SDK** (`natlas_kit`) | `chat`, `stream`, `translate`, `detect_language`, `classify`, `classify_scam`. Zero dependencies, works with any OpenAI-compatible N-ATLAS deployment (LM Studio, llama.cpp, vLLM, Ollama, hosted) |
| **CLI** (`natlas`) | `doctor`, `chat`, `translate`, `scam`, `eval`, `serve` |
| **REST API** (`natlas serve`) | Task endpoints `/v1/translate`, `/v1/scam-check`, `/v1/detect`, `/v1/chat`, plus Swagger docs at `/docs` |
| **Eval harness** (`natlas eval`) | One-command benchmark: scam detection F1, EN→YO/HA/IG chrF, language ID; accepts your own JSONL |
| **Reference app** (Ṣọ́ra) | Streamlit scam checker for SMS/WhatsApp messages in 5 Nigerian languages, built entirely on the kit |

## Quick start (Mac M-series, 16 GB RAM)

```bash
# 1. Run N-ATLAS locally (downloads Q4_K_M GGUF ~4.9 GB, loads it in LM Studio on :1234)
bash setup_model.sh

# 2. Install the kit
python3 -m pip install -e ".[server,demo,dev]"

# 3. Check everything works
natlas doctor

# 4. Use it
natlas translate "Where is the hospital?" --to ha
natlas scam "Your BVN has been blocked, send your PIN to reactivate"
natlas chat
natlas eval                 # writes eval_results/<timestamp>_report.json
natlas serve --port 8000    # REST API, docs at http://localhost:8000/docs
streamlit run apps/scam_checker/app.py
```

### Python

```python
from natlas_kit import NAtlas
nt = NAtlas()  # default http://localhost:1234/v1, model "n-atlas"
nt.translate("Thank you very much", target="ig")
nt.classify_scam("Oga, EFCC don flag your account. Pay clearance fee of N30,000")
# {'label': 'scam', 'risk': 92, 'reasons': [...], 'rule_flags': [...], 'advice': '...', 'language': 'pcm'}
```

Point the kit at any deployment with `NATLAS_BASE_URL`, `NATLAS_MODEL` and `NATLAS_API_KEY`.

## Architecture

```
 your app / notebook / CLI
          │
   natlas_kit SDK  ──►  prompts tuned for N-ATLAS + rule-based fraud signals
          │
 OpenAI-compatible endpoint (LM Studio · llama.cpp · vLLM · hosted)
          │
   N-ATLaS (Llama-3-8B, NCAIR1) — GGUF Q4_K_M locally or full weights on GPU
```

## Tests

`pytest` runs the full test suite offline against a fake server, so no model is needed.

## Data note

`natlas_kit/eval/data/*.jsonl` are small seed sets. Native-speaker review is ongoing, and contributions are welcome.

## License
MIT for the kit code. N-ATLaS model weights are subject to NCAIR's own licence.
