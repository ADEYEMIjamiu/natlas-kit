"""N-ATLAS Kit REST API — task-level endpoints on top of any N-ATLAS deployment.

POST /v1/translate   {"text": "...", "target": "yo", "source": "auto"}
POST /v1/scam-check  {"text": "..."}
POST /v1/detect      {"text": "..."}
POST /v1/chat        {"message": "...", "system": null}
GET  /health
Interactive docs at /docs (Swagger)."""
from __future__ import annotations

import time

from .client import LANGUAGES, NAtlas, NAtlasError

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError as e:  # pragma: no cover
    raise SystemExit("Install server extras: pip install 'natlas-kit[server]'") from e

app = FastAPI(title="N-ATLAS Kit API", version="0.1.0",
              description="Task-level REST API for N-ATLAS (Yoruba, Hausa, Igbo, Nigerian English, Pidgin).")
nt = NAtlas()
LOG: list[dict] = []  # in-memory request log used for validation evidence (session logs)


class TextIn(BaseModel):
    text: str


class TranslateIn(TextIn):
    target: str
    source: str = "auto"


class ChatIn(BaseModel):
    message: str
    system: str | None = None


def _wrap(endpoint: str, fn, payload: dict):
    t0 = time.time()
    try:
        out = fn()
    except NAtlasError as e:
        raise HTTPException(503, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    LOG.append({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "endpoint": endpoint,
                "latency_ms": round((time.time() - t0) * 1000), "chars": len(str(payload))})
    return out


@app.get("/health")
def health():
    return {**nt.health(), "languages": LANGUAGES}


@app.post("/v1/translate")
def translate(body: TranslateIn):
    return _wrap("translate", lambda: {"translation": nt.translate(body.text, body.target, body.source)}, body.model_dump())


@app.post("/v1/scam-check")
def scam(body: TextIn):
    def go():
        r = nt.classify_scam(body.text); r.pop("raw", None); return r
    return _wrap("scam-check", go, body.model_dump())


@app.post("/v1/detect")
def detect(body: TextIn):
    return _wrap("detect", lambda: {"language": nt.detect_language(body.text)}, body.model_dump())


@app.post("/v1/chat")
def chat(body: ChatIn):
    return _wrap("chat", lambda: {"reply": nt.chat(body.message, system=body.system)}, body.model_dump())


@app.get("/stats")
def stats():
    return {"requests": len(LOG), "recent": LOG[-50:]}


def serve(host="0.0.0.0", port=8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)
