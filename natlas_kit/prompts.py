"""Prompt templates tuned for N-ATLAS (Llama-3-8B based, Yoruba/Hausa/Igbo/Nigerian English)."""
from __future__ import annotations

import json
import re

SYSTEM_DEFAULT = (
    "You are N-ATLAS, a helpful Nigerian AI assistant. You understand Yoruba, Hausa, Igbo, "
    "Nigerian Pidgin and Nigerian English. Reply in the same language the user writes in, "
    "clearly and concisely."
)


FEW_SHOT = {
    "Yoruba": [("Good evening, my friend.", "Ẹ kú ìrọ̀lẹ́, ọ̀rẹ́ mi."), ("I want to buy bread.", "Mo fẹ́ ra búrẹ́dì.")],
    "Hausa": [("Good evening, my friend.", "Barka da yamma, abokina."), ("I want to buy bread.", "Ina so in sayi burodi.")],
    "Igbo": [("Good evening, my friend.", "Ezi mgbede, enyi m."), ("I want to buy bread.", "Achọrọ m ịzụta achịcha.")],
}


def translate_messages(text: str, target: str, source: str | None):
    src = f" from {source}" if source else ""
    msgs = [{"role": "system", "content": f"You are a professional Nigerian translator. Translate faithfully into natural, everyday {target}"
             + (" with correct tone marks" if target == "Yoruba" else "") + ". Keep the meaning and sentence type (a question stays a question). Output ONLY the translation."}]
    for en, tgt in FEW_SHOT.get(target, []):
        msgs += [{"role": "user", "content": f"Translate into {target}: {en}"}, {"role": "assistant", "content": tgt}]
    msgs.append({"role": "user", "content": f"Translate{src} into {target}: {text}"})
    return msgs


def detect_messages(text: str, languages: dict):
    opts = ", ".join(f"{k} ({v})" for k, v in languages.items())
    return [
        {"role": "system", "content": "You identify languages. Answer with the code only."},
        {"role": "user", "content": f"Which language is this text? Options: {opts}.\nText: {text}\nCode:"},
    ]


def classify_messages(text: str, labels: list[str], instruction: str = ""):
    return [
        {"role": "system", "content": "You are a precise text classifier. Answer with exactly one label."},
        {"role": "user", "content": f"{instruction}\nLabels: {', '.join(labels)}\nText: {text}\nLabel:"},
    ]


SCAM_SYSTEM = """You are a fraud-prevention assistant for Nigerians. You read SMS, WhatsApp messages, emails and job adverts written in English, Nigerian Pidgin, Yoruba, Hausa or Igbo, and decide if they are a SCAM or LEGIT.
Common Nigerian scam signs: requests for BVN, NIN, ATM PIN, OTP or card details; "your account is blocked/suspended"; fake bank alerts; upfront "processing", "registration" or "clearance" fees; jobs or loans that are too good to be true; urgent pressure; unknown links; impersonating banks, CBN, EFCC, NIMC, telcos or family members.
NOT scams: genuine OTP/receipt/transaction alerts that WARN you not to share codes, appointment reminders, delivery notices, normal chats between friends and family, community meeting announcements.
Respond ONLY with JSON: {"label": "scam" or "legit", "risk": 0-100, "reasons": ["short reason", ...], "advice": "one sentence of advice written in the SAME language as the message"}"""


def scam_messages(text: str):
    return [
        {"role": "system", "content": SCAM_SYSTEM},
        {"role": "user", "content": f"Message:\n\"\"\"{text}\"\"\"\nJSON:"},
    ]


# Rule-based signals blended with the model output so the demo stays robust on a quantized 8B model.
RED_FLAGS = {
    r"\b(bvn|nin)\b": "Asks about BVN/NIN",
    r"\b(pin|otp|cvv|token code)\b": "Asks for PIN/OTP/card secret",
    r"(blocked|suspended|deactivated|restricted)": "Claims your account is blocked",
    r"(processing|registration|clearance|activation|delivery)\s+fee": "Upfront fee requested",
    r"(urgent|immediately|within 24 ?hours|now now|sharp sharp)": "Urgency pressure",
    r"(congratulations|you have won|you won|winner|lucky)": "Unexpected prize",
    r"(bit\.ly|tinyurl|wa\.me|http[s]?://\S+)": "Contains a link",
    r"(double your|guaranteed returns?|invest .* get)": "Too-good-to-be-true returns",
    r"(send|pay|transfer)\b.{0,30}\b(₦|naira|n\d|\d{3,})": "Asks you to send money",
}


SAFE_SIGNALS = {
    r"(do not|don't|never) share": "Warns you not to share codes (typical of genuine alerts)",
    r"never (charge|ask)": "States it never charges or asks for secrets",
    r"(transfer|payment|recharge|order).{0,40}(successful|confirmed)": "Looks like a transaction receipt",
    r"\bbalance\b": "Shows an account balance (receipt style)",
}


def safe_flags(text: str) -> list[str]:
    low = text.lower()
    return [why for pat, why in SAFE_SIGNALS.items() if re.search(pat, low)]


def rule_flags(text: str) -> list[str]:
    low = text.lower()
    return [why for pat, why in RED_FLAGS.items() if re.search(pat, low)]


def parse_scam_json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.S)
    data = {}
    if m:
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            data = {}
    label = str(data.get("label", "")).lower()
    if label not in ("scam", "legit"):
        label = "scam" if "scam" in raw.lower() else "legit"
    try:
        risk = int(float(data.get("risk", 80 if label == "scam" else 20)))
    except (TypeError, ValueError):
        risk = 80 if label == "scam" else 20
    reasons = data.get("reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    return {
        "label": label,
        "risk": max(0, min(100, risk)),
        "reasons": [str(r) for r in reasons][:5],
        "advice": str(data.get("advice", "")),
        "raw": raw,
    }


def blend(model_result: dict, text: str) -> dict:
    """Combine model verdict with red-flag and safe-signal rules; risk = 0.7*model + 0.3*rules."""
    flags = rule_flags(text)
    safe = safe_flags(text)
    rule_risk = max(0, min(100, 25 * len(flags) - 35 * len(safe)))
    risk = round(0.7 * model_result["risk"] + 0.3 * rule_risk)
    if safe and not re.search(r"(fee|send|pay|click|link|http)", text.lower()):
        risk = min(risk, 45)  # protective wording and no ask: cap risk
    out = dict(model_result)
    out["rule_flags"] = flags
    out["safe_signals"] = safe
    out["risk"] = risk
    out["label"] = "scam" if risk >= 50 else "legit"
    return out


def strip_wrapping(s: str) -> str:
    s = s.strip().strip('"').strip()
    s = re.sub(r"^(translation|yoruba|hausa|igbo|english|pidgin)[^:]{0,20}:\s*", "", s, flags=re.I)
    return s.split("\n\n")[0].strip()
