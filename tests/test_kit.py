"""Offline tests: spin up a fake OpenAI-compatible server so no model is needed."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from natlas_kit import NAtlas
from natlas_kit.eval.harness import chrf, prf
from natlas_kit.prompts import parse_scam_json, rule_flags


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self._send({"data": [{"id": "n-atlas"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        sys_msg = body["messages"][0]["content"]
        user = body["messages"][-1]["content"]
        if "fraud-prevention" in sys_msg:
            scam = any(w in user.lower() for w in ["pin", "fee", "bvn", "otp"])
            reply = json.dumps({"label": "scam" if scam else "legit", "risk": 90 if scam else 10, "reasons": ["test"], "advice": "ok"})
        elif "identify languages" in sys_msg:
            reply = "yo" if "Ẹ" in user else "en"
        elif "translator" in sys_msg:
            reply = "Yoruba translation: Ẹ kaarọ."
        else:
            reply = "Báwo ni!"
        self._send({"choices": [{"message": {"content": reply}}], "usage": {"prompt_tokens": 5, "completion_tokens": 3}})

    def _send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)


@pytest.fixture(scope="module")
def nt():
    srv = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield NAtlas(base_url=f"http://127.0.0.1:{srv.server_port}/v1")
    srv.shutdown()


def test_health(nt):
    assert nt.health()["model_loaded"]


def test_chat(nt):
    assert nt.chat("hi") == "Báwo ni!"


def test_translate_strips_prefix(nt):
    assert nt.translate("Good morning", target="yo") == "Ẹ kaarọ."


def test_scam(nt):
    r = nt.classify_scam("Your BVN is blocked, send your PIN now")
    assert r["label"] == "scam" and r["risk"] >= 50 and r["rule_flags"]
    assert nt.classify_scam("See you at the meeting tomorrow")["label"] == "legit"


def test_bad_lang(nt):
    with pytest.raises(ValueError):
        nt.translate("x", target="fr")


def test_metrics():
    assert chrf("Ẹ kaarọ", "Ẹ kaarọ") == pytest.approx(100)
    assert chrf("abc", "xyz") == 0
    assert prf(["scam", "legit"], ["scam", "scam"])["recall"] == 1.0


def test_parse_garbage():
    assert parse_scam_json("I think this is a scam")["label"] == "scam"
    assert "Asks for PIN/OTP/card secret" in rule_flags("send your OTP")


def test_eval_runs(nt, tmp_path):
    from natlas_kit.eval import harness
    rep = harness.run(nt, out_dir=tmp_path, log=lambda *a: None)
    assert rep["results"]["scam"]["n"] == 36
