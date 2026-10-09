"""`natlas` command line: doctor | chat | translate | scam | eval | serve"""
from __future__ import annotations

import argparse
import json
import sys

from .client import NAtlas, NAtlasError


def main(argv=None):
    ap = argparse.ArgumentParser(prog="natlas", description="N-ATLAS Kit — developer toolkit for Nigeria's LLM")
    ap.add_argument("--base-url", help="OpenAI-compatible endpoint (default env NATLAS_BASE_URL or http://localhost:1234/v1)")
    ap.add_argument("--model", help="model id (default env NATLAS_MODEL or n-atlas)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="check the N-ATLAS server is reachable and the model is loaded")
    c = sub.add_parser("chat", help="interactive chat (or one-shot with a message)"); c.add_argument("message", nargs="*")
    t = sub.add_parser("translate", help="translate text"); t.add_argument("text"); t.add_argument("--to", required=True, choices=["en", "yo", "ha", "ig", "pcm"])
    s = sub.add_parser("scam", help="check if a message is a scam"); s.add_argument("text")
    e = sub.add_parser("eval", help="benchmark the model"); e.add_argument("--tasks", default="scam,translate,langid")
    e.add_argument("--scam-data"); e.add_argument("--translate-data"); e.add_argument("--out", default="eval_results")
    v = sub.add_parser("serve", help="run the N-ATLAS Kit REST API"); v.add_argument("--port", type=int, default=8000); v.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args(argv)

    kw = {k: v for k, v in {"base_url": a.base_url, "model": a.model}.items() if v}
    nt = NAtlas(**kw)
    try:
        if a.cmd == "doctor":
            h = nt.health(); print(json.dumps(h, indent=2))
            if h.get("ok") and h.get("model_loaded"):
                print("Smoke test:", nt.chat("Say hello in Yoruba, Hausa and Igbo.", max_tokens=80))
            sys.exit(0 if h.get("ok") else 1)
        elif a.cmd == "chat":
            if a.message:
                print(nt.chat(" ".join(a.message))); return
            hist = []
            print("N-ATLAS chat — type 'exit' to quit")
            while (msg := input("you> ").strip()) not in ("exit", "quit"):
                hist_reply = "".join(_print_stream(nt.stream([{"role": "system", "content": "You are N-ATLAS, a helpful Nigerian assistant."}, *hist, {"role": "user", "content": msg}])))
                hist += [{"role": "user", "content": msg}, {"role": "assistant", "content": hist_reply}]
        elif a.cmd == "translate":
            print(nt.translate(a.text, target=a.to))
        elif a.cmd == "scam":
            r = nt.classify_scam(a.text); r.pop("raw", None); print(json.dumps(r, indent=2, ensure_ascii=False))
        elif a.cmd == "eval":
            from .eval import harness
            data = {"scam": a.scam_data, "translate": a.translate_data, "langid": a.scam_data}
            rep = harness.run(nt, tasks=a.tasks.split(","), data=data, out_dir=a.out)
            print("\n" + json.dumps(rep, indent=2, ensure_ascii=False))
        elif a.cmd == "serve":
            from .server import serve
            serve(host=a.host, port=a.port)
    except NAtlasError as err:
        print(f"Error: {err}", file=sys.stderr); sys.exit(2)


def _print_stream(gen):
    print("n-atlas> ", end="", flush=True)
    for tok in gen:
        print(tok, end="", flush=True); yield tok
    print()


if __name__ == "__main__":
    main()
