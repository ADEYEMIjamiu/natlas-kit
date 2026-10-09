"""Ṣọ́ra (Watch out!) — multilingual scam checker built with N-ATLAS Kit.
Run: streamlit run apps/scam_checker/app.py"""
import csv
import os
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from natlas_kit import NAtlas, NAtlasError  # noqa: E402

LOG = Path(__file__).parent / "session_log.csv"
LANG_NAMES = {"en": "English", "yo": "Yorùbá", "ha": "Hausa", "ig": "Igbo", "pcm": "Pidgin"}
EXAMPLES = {
    "Fake bank (English)": "Dear customer, your BVN has been blocked by CBN. Click http://bit.ly/bvn-update and enter your ATM PIN within 24 hours.",
    "Family emergency (Pidgin)": "Mummy this is my new number, my phone fell inside water. Abeg send 20k to this account urgently.",
    "Prize scam (Yorùbá)": "Ẹ ku oriire! Ẹ ti jẹ ẹbun N300,000. Ẹ san owo N5,000 lati gba ẹbun yin.",
    "Account blocked (Hausa)": "An toshe asusun ku na banki. Ku turo mana lambar PIN da OTP dinku domin a bude shi yanzu.",
    "Normal message (Igbo)": "Kedu ka ị mere? Aga m abịa ụlọ gị echi.",
}

st.set_page_config(page_title="Ṣọ́ra — Scam Checker", page_icon="🛡️", layout="centered")
st.title("🛡️ Ṣọ́ra — Is this message a scam?")
st.caption("Paste any SMS, WhatsApp message, email or job advert in English, Pidgin, Yorùbá, Hausa or Igbo. Powered by N-ATLAS, Nigeria's LLM, via N-ATLAS Kit.")

with st.sidebar:
    base = st.text_input("N-ATLAS endpoint", os.getenv("NATLAS_BASE_URL", "http://localhost:1234/v1"))
    model = st.text_input("Model id", os.getenv("NATLAS_MODEL", "n-atlas"))
    nt = NAtlas(base_url=base, model=model)
    h = nt.health()
    st.success("Model online") if h.get("ok") else st.error("Model offline — start LM Studio server")
    tester = st.text_input("Your name / tester ID (optional)")

ex = st.selectbox("Try an example", ["—"] + list(EXAMPLES))
text = st.text_area("Message", EXAMPLES.get(ex, ""), height=140)

if st.button("Check message", type="primary", disabled=not text.strip()):
    t0 = time.time()
    try:
        with st.spinner("N-ATLAS is reading the message…"):
            r = nt.classify_scam(text)
    except NAtlasError as e:
        st.error(str(e)); st.stop()
    secs = time.time() - t0
    risk = r["risk"]
    if r["label"] == "scam":
        st.error(f"⚠️ LIKELY SCAM — risk {risk}/100")
    else:
        st.success(f"✅ Looks safe — risk {risk}/100")
    st.progress(risk / 100)
    st.write(f"**Detected language:** {LANG_NAMES.get(r['language'], r['language'])}")
    if r["advice"]:
        st.info(f"**Advice:** {r['advice']}")
    reasons = list(dict.fromkeys(r["reasons"] + r.get("rule_flags", [])))
    if reasons:
        st.write("**Why:**"); [st.write(f"- {x}") for x in reasons]
    st.caption(f"Answered in {secs:.1f}s by {model}")
    st.session_state["last"] = {"text": text, **r, "secs": round(secs, 2)}

if "last" in st.session_state:
    fb = st.radio("Was this correct?", ["—", "Yes 👍", "No 👎"], horizontal=True)
    if fb != "—" and st.button("Submit feedback"):
        last = st.session_state.pop("last")
        new = not LOG.exists()
        with LOG.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["timestamp", "tester", "language", "label", "risk", "latency_s", "feedback", "message"])
            w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), tester, last["language"], last["label"], last["risk"], last["secs"], fb, last["text"]])
        st.toast("Thanks! Feedback saved.")
