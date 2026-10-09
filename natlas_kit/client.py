"""Thin, dependency-light client for N-ATLAS served behind any OpenAI-compatible API
(LM Studio, llama.cpp server, vLLM, Ollama /v1, or a hosted endpoint)."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Iterator

from . import langid, prompts

LANGUAGES = {
    "en": "Nigerian English",
    "yo": "Yoruba",
    "ha": "Hausa",
    "ig": "Igbo",
    "pcm": "Nigerian Pidgin",
}


class NAtlasError(RuntimeError):
    pass


@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0


@dataclass
class NAtlas:
    base_url: str = field(default_factory=lambda: os.getenv("NATLAS_BASE_URL", "http://localhost:1234/v1"))
    model: str = field(default_factory=lambda: os.getenv("NATLAS_MODEL", "n-atlas"))
    api_key: str = field(default_factory=lambda: os.getenv("NATLAS_API_KEY", "not-needed"))
    timeout: float = 120.0
    temperature: float = 0.2
    usage: Usage = field(default_factory=Usage)

    # ---------------- low level ----------------
    def _post(self, path: str, payload: dict, stream: bool = False):
        req = urllib.request.Request(
            self.base_url.rstrip("/") + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        try:
            return urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            raise NAtlasError(f"HTTP {e.code}: {e.read().decode(errors='ignore')[:300]}") from e
        except urllib.error.URLError as e:
            raise NAtlasError(
                f"Cannot reach N-ATLAS server at {self.base_url} ({e.reason}). "
                "Start it with LM Studio (`lms server start`) or run `natlas doctor`."
            ) from e

    def complete(self, messages: list[dict], max_tokens: int = 512, temperature: float | None = None, **extra) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self.temperature if temperature is None else temperature,
            **extra,
        }
        t0 = time.time()
        with self._post("/chat/completions", payload) as r:
            data = json.loads(r.read())
        self.usage.calls += 1
        self.usage.seconds += time.time() - t0
        u = data.get("usage") or {}
        self.usage.prompt_tokens += u.get("prompt_tokens", 0)
        self.usage.completion_tokens += u.get("completion_tokens", 0)
        return data["choices"][0]["message"]["content"].strip()

    def stream(self, messages: list[dict], max_tokens: int = 512) -> Iterator[str]:
        payload = {"model": self.model, "messages": messages, "max_tokens": max_tokens,
                   "temperature": self.temperature, "stream": True}
        with self._post("/chat/completions", payload) as r:
            for raw in r:
                line = raw.decode().strip()
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                delta = json.loads(chunk)["choices"][0].get("delta", {}).get("content")
                if delta:
                    yield delta

    def health(self) -> dict:
        try:
            with urllib.request.urlopen(self.base_url.rstrip("/") + "/models", timeout=10) as r:
                models = [m["id"] for m in json.loads(r.read()).get("data", [])]
            return {"ok": True, "base_url": self.base_url, "models": models, "model_loaded": self.model in models}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "base_url": self.base_url, "error": str(e)}

    # ---------------- high level tasks ----------------
    def chat(self, message: str, system: str | None = None, history: list[dict] | None = None, **kw) -> str:
        msgs = [{"role": "system", "content": system or prompts.SYSTEM_DEFAULT}]
        msgs += history or []
        msgs.append({"role": "user", "content": message})
        return self.complete(msgs, **kw)

    def translate(self, text: str, target: str, source: str = "auto", **kw) -> str:
        _check_lang(target)
        msgs = prompts.translate_messages(text, LANGUAGES[target], None if source == "auto" else LANGUAGES[_check_lang(source)])
        out = self.complete(msgs, temperature=0.0, **kw)
        return prompts.strip_wrapping(out)

    def detect_language(self, text: str, min_confidence: float = 0.45) -> str:
        """Hybrid: lexical markers first (instant), N-ATLAS when the text is ambiguous."""
        code, conf = langid.guess(text)
        if conf >= min_confidence:
            return code
        out = self.complete(prompts.detect_messages(text, LANGUAGES), temperature=0.0, max_tokens=8).lower()
        for code in LANGUAGES:
            if re.search(rf"\b{code}\b", out):
                return code
        return "en"

    def classify(self, text: str, labels: list[str], instruction: str = "") -> str:
        out = self.complete(prompts.classify_messages(text, labels, instruction), temperature=0.0, max_tokens=10)
        low = out.lower()
        for lab in sorted(labels, key=len, reverse=True):
            if lab.lower() in low:
                return lab
        return labels[-1]

    def classify_scam(self, text: str) -> dict:
        """Returns {'label': 'scam'|'legit', 'risk': 0-100, 'reasons': [...], 'advice': str, 'language': code}."""
        raw = self.complete(prompts.scam_messages(text), temperature=0.0, max_tokens=300)
        result = prompts.blend(prompts.parse_scam_json(raw), text)
        result["language"] = self.detect_language(text)
        return result


def _check_lang(code: str) -> str:
    if code not in LANGUAGES:
        raise ValueError(f"Unsupported language '{code}'. Use one of {list(LANGUAGES)}")
    return code
