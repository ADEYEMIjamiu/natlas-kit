"""Fast lexical language ID for Nigerian languages; the SDK falls back to N-ATLAS when unsure."""
from __future__ import annotations

import re

MARKERS = {
    "yo": {"chars": "ẹṣɛ", "words": {"ni", "ti", "mo", "ẹ", "rẹ", "yin", "wa", "lati", "si", "ṣe", "kaaro", "bawo", "oriire", "owo", "yii", "ọjọ"}},
    "ig": {"chars": "ụị", "words": {"ka", "nke", "m", "gị", "anyị", "ga", "na", "kedu", "aga", "echi", "ego", "ụlọ", "ozugbo"}},
    "ha": {"chars": "ƙɗɓ", "words": {"da", "ku", "na", "zan", "yana", "kuma", "domin", "ina", "kwana", "gobe", "barka", "kun", "yanzu", "mana", "asusun"}},
    "pcm": {"chars": "", "words": {"don", "dey", "abeg", "wetin", "una", "dem", "sabi", "oga", "na", "go", "make", "wey", "sharp", "how far", "no be", "fit", "am"}},
}
EN_WORDS = {"the", "your", "you", "is", "has", "been", "to", "and", "of", "for", "with", "this", "please", "will", "are", "have"}


def guess(text: str) -> tuple[str, float]:
    low = text.lower()
    toks = re.findall(r"[\w\u0300-\u036f']+", low)
    tokset = set(toks)
    scores = {}
    for code, m in MARKERS.items():
        sc = 3 * sum(low.count(c) for c in m["chars"])
        sc += sum(2 for w in m["words"] if (" " in w and w in low) or w in tokset)
        scores[code] = sc
    en = sum(1 for t in toks if t in EN_WORDS)
    # Pidgin = English-ish text with Pidgin markers
    if scores["pcm"] >= 4 and scores["pcm"] >= en:
        scores["pcm"] += en
    scores["en"] = en * 1.5 if scores["pcm"] < 4 else en
    best = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    return best, scores[best] / total
