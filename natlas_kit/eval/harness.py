"""N-ATLAS eval harness: one command to benchmark any N-ATLAS deployment on Nigerian-language tasks.

Tasks
  scam      : scam vs legit message classification (accuracy, precision, recall, F1, per-language)
  translate : English -> Yoruba/Hausa/Igbo (chrF++ style character n-gram F-score, per-language)
  langid    : language identification (accuracy)
Any task accepts a custom JSONL file, so teams can plug in their own data."""
from __future__ import annotations

import json
import re
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).parent / "data"


def load_jsonl(path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


# ---------------- metrics ----------------
def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s.lower().strip())


def strip_tones(s: str) -> str:
    """Remove tone marks/underdots: Yoruba is often written without them in everyday text."""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def chrf(hyp: str, ref: str, n: int = 6, beta: float = 2.0, ignore_tones: bool = False) -> float:
    """Character n-gram F-score (chrF, Popović 2015), 0-100."""
    hyp, ref = _norm(hyp).replace(" ", ""), _norm(ref).replace(" ", "")
    hyp = re.sub(r"[.?!,]", "", hyp); ref = re.sub(r"[.?!,]", "", ref)
    if ignore_tones:
        hyp, ref = strip_tones(hyp), strip_tones(ref)
    precs, recs = [], []
    for k in range(1, n + 1):
        h = Counter(hyp[i:i + k] for i in range(len(hyp) - k + 1))
        r = Counter(ref[i:i + k] for i in range(len(ref) - k + 1))
        if not h or not r:
            continue
        overlap = sum((h & r).values())
        precs.append(overlap / sum(h.values()))
        recs.append(overlap / sum(r.values()))
    if not precs:
        return 0.0
    p, r = sum(precs) / len(precs), sum(recs) / len(recs)
    if p + r == 0:
        return 0.0
    return 100 * (1 + beta**2) * p * r / (beta**2 * p + r)


def prf(golds, preds, pos="scam"):
    tp = sum(g == pos and p == pos for g, p in zip(golds, preds))
    fp = sum(g != pos and p == pos for g, p in zip(golds, preds))
    fn = sum(g == pos and p != pos for g, p in zip(golds, preds))
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = sum(g == p for g, p in zip(golds, preds)) / len(golds)
    return {"accuracy": round(acc, 3), "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3)}


# ---------------- tasks ----------------
def run_scam(nt, path=None, log=print):
    rows = load_jsonl(path or DATA / "scam_seed.jsonl")
    golds, preds, by_lang, details = [], [], defaultdict(lambda: [0, 0]), []
    for i, row in enumerate(rows, 1):
        res = nt.classify_scam(row["text"])
        golds.append(row["label"]); preds.append(res["label"])
        by_lang[row.get("lang", "?")][0] += res["label"] == row["label"]
        by_lang[row.get("lang", "?")][1] += 1
        details.append({**row, "pred": res["label"], "risk": res["risk"]})
        log(f"  [{i}/{len(rows)}] {row.get('lang','?'):>3} gold={row['label']:<5} pred={res['label']:<5} risk={res['risk']}")
    out = prf(golds, preds)
    out["per_language_accuracy"] = {k: round(c / t, 3) for k, (c, t) in by_lang.items()}
    out["n"] = len(rows)
    return out, details


def run_translate(nt, path=None, log=print):
    rows = load_jsonl(path or DATA / "translate_seed.jsonl")
    scores, scores_nt, by_lang, details = [], [], defaultdict(list), []
    for i, row in enumerate(rows, 1):
        hyp = nt.translate(row["src"], target=row["lang"], source="en", max_tokens=120)
        s = chrf(hyp, row["tgt"]); s2 = chrf(hyp, row["tgt"], ignore_tones=True)
        scores.append(s); scores_nt.append(s2); by_lang[row["lang"]].append(s)
        details.append({**row, "hyp": hyp, "chrf": round(s, 1), "chrf_no_tones": round(s2, 1)})
        log(f"  [{i}/{len(rows)}] {row['lang']} chrF={s:5.1f} | {hyp[:60]}")
    return {"chrf": round(sum(scores) / len(scores), 1),
            "chrf_ignoring_tone_marks": round(sum(scores_nt) / len(scores_nt), 1),
            "per_language_chrf": {k: round(sum(v) / len(v), 1) for k, v in by_lang.items()},
            "n": len(rows)}, details


def run_langid(nt, path=None, log=print):
    rows = load_jsonl(path or DATA / "scam_seed.jsonl")
    correct, details = 0, []
    for i, row in enumerate(rows, 1):
        pred = nt.detect_language(row["text"])
        correct += pred == row["lang"]
        details.append({"text": row["text"], "gold": row["lang"], "pred": pred})
        log(f"  [{i}/{len(rows)}] gold={row['lang']:>3} pred={pred}")
    return {"accuracy": round(correct / len(rows), 3), "n": len(rows)}, details


TASKS = {"scam": run_scam, "translate": run_translate, "langid": run_langid}


def run(nt, tasks=("scam", "translate", "langid"), data=None, out_dir="eval_results", log=print):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    report = {"model": nt.model, "base_url": nt.base_url, "timestamp": stamp, "results": {}}
    t0 = time.time()
    for t in tasks:
        log(f"\n== {t} ==")
        summary, details = TASKS[t](nt, (data or {}).get(t), log=log)
        report["results"][t] = summary
        (out_dir / f"{stamp}_{t}_details.jsonl").write_text(
            "\n".join(json.dumps(d, ensure_ascii=False) for d in details), encoding="utf-8")
    report["seconds"] = round(time.time() - t0, 1)
    report["calls"] = nt.usage.calls
    (out_dir / f"{stamp}_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
