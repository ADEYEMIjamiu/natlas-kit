"""N-ATLAS Kit REST API — task-level endpoints on top of any N-ATLAS deployment.

POST /v1/translate   {"text": "...", "target": "yo", "source": "auto"}
POST /v1/scam-check  {"text": "..."}
POST /v1/detect      {"text": "..."}
POST /v1/chat        {"message": "...", "system": null}
GET  /health
Interactive docs at /docs (Swagger)."""
from __future__ import annotations

import contextvars
import os
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
LOG: list[dict] = []
_CURRENT_AUTH: contextvars.ContextVar = contextvars.ContextVar("auth", default="")


@app.middleware("http")
async def _capture_auth(request, call_next):
    _CURRENT_AUTH.set(request.headers.get("authorization", ""))
    return await call_next(request)  # in-memory request log used for validation evidence (session logs)


class TextIn(BaseModel):
    text: str


class TranslateIn(TextIn):
    target: str
    source: str = "auto"


class ChatIn(BaseModel):
    message: str
    system: str | None = None


def _wrap(endpoint: str, fn, payload: dict):
    key = os.getenv("NATLAS_GATEWAY_KEY", "")
    if key and _CURRENT_AUTH.get() != f"Bearer {key}":
        raise HTTPException(401, "Missing or wrong API key")
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


# ---------------------------------------------------------------------------
# Gateway mode: securely share one N-ATLAS deployment with remote developers.
# Proxies the OpenAI-compatible routes to the upstream server (e.g. LM Studio),
# with an API key, a per-client rate limit and a CSV usage log (validation evidence).
# Enable by setting NATLAS_GATEWAY_KEY before `natlas serve`.
# ---------------------------------------------------------------------------
import csv
import json as _json
import os
import urllib.error
import urllib.request
from collections import defaultdict, deque
from pathlib import Path

from fastapi import Body, Request
from fastapi.responses import JSONResponse, StreamingResponse

UPSTREAM = os.getenv("NATLAS_UPSTREAM", "http://localhost:1234/v1").rstrip("/")
GATEWAY_KEY = os.getenv("NATLAS_GATEWAY_KEY", "")
GATEWAY_LOG = Path(os.getenv("NATLAS_GATEWAY_LOG", "gateway_log.csv"))
RATE = int(os.getenv("NATLAS_RATE_PER_MIN", "30"))
_hits: dict = defaultdict(deque)


def _client(request: Request) -> str:
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")


def _guard(request: Request):
    if GATEWAY_KEY and request.headers.get("authorization", "") != f"Bearer {GATEWAY_KEY}":
        raise HTTPException(401, "Missing or wrong API key")
    q = _hits[_client(request)]
    now = time.time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE:
        raise HTTPException(429, "Rate limit: please wait a minute")
    q.append(now)


def _log(request: Request, route: str, ms: int, tokens: int, status: int):
    new = not GATEWAY_LOG.exists()
    with GATEWAY_LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "client", "tester", "route", "latency_ms", "completion_tokens", "status"])
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), _client(request), request.headers.get("x-tester", ""),
                    route, ms, tokens, status])


@app.get("/v1/models")
def gw_models(request: Request):
    _guard(request)
    with urllib.request.urlopen(UPSTREAM + "/models", timeout=15) as r:
        return JSONResponse(_json.loads(r.read()))


@app.post("/v1/chat/completions")
def gw_chat(request: Request, body: dict = Body(...)):
    _guard(request)
    t0 = time.time()
    req = urllib.request.Request(UPSTREAM + "/chat/completions", data=_json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        up = urllib.request.urlopen(req, timeout=300)
    except urllib.error.URLError as e:
        _log(request, "chat/completions", round((time.time() - t0) * 1000), 0, 503)
        raise HTTPException(503, f"N-ATLAS upstream unavailable: {e}") from e
    if body.get("stream"):
        def gen():
            try:
                for line in up:
                    yield line
            finally:
                up.close()
                _log(request, "chat/completions(stream)", round((time.time() - t0) * 1000), 0, 200)
        return StreamingResponse(gen(), media_type="text/event-stream")
    data = _json.loads(up.read()); up.close()
    _log(request, "chat/completions", round((time.time() - t0) * 1000),
         (data.get("usage") or {}).get("completion_tokens", 0), 200)
    return JSONResponse(data)
