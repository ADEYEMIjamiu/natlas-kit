"""N-ATLAS Kit Playground: try every SDK capability interactively and copy the matching code."""
import os
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from natlas_kit import LANGUAGES, NAtlas, NAtlasError  # noqa: E402

st.set_page_config(page_title="N-ATLAS Kit Playground", page_icon="🧪", layout="wide")
st.title("🧪 N-ATLAS Kit Playground")
st.caption("Try N-ATLAS in Yoruba, Hausa, Igbo, Pidgin and Nigerian English, then copy the Python that does the same thing.")

base = st.sidebar.text_input("N-ATLAS endpoint", os.getenv("NATLAS_BASE_URL", "http://localhost:1234/v1"))
model = st.sidebar.text_input("Model id", os.getenv("NATLAS_MODEL", "n-atlas"))
temp = st.sidebar.slider("Temperature", 0.0, 1.0, 0.2, 0.1)
nt = NAtlas(base_url=base, model=model, temperature=temp)

tab_chat, tab_tr, tab_lid, tab_cls = st.tabs(["💬 Chat", "🌍 Translate", "🔎 Detect language", "🏷️ Classify"])


def run(fn, code):
    t0 = time.time()
    try:
        out = fn()
    except NAtlasError as e:
        st.error(str(e)); return
    st.success(out if isinstance(out, str) else "Done")
    if not isinstance(out, str):
        st.json(out)
    st.caption(f"{time.time()-t0:.1f}s")
    st.code(code, language="python")


with tab_chat:
    msg = st.text_area("Message", "Ṣé o lè ṣàlàyé ohun tí AI jẹ́ ní ṣókí?")
    sys_p = st.text_input("System prompt (optional)", "")
    if st.button("Send", key="chat"):
        run(lambda: nt.chat(msg, system=sys_p or None),
            f'from natlas_kit import NAtlas\nnt = NAtlas()\nprint(nt.chat({msg!r}))')

with tab_tr:
    c1, c2 = st.columns(2)
    src_text = c1.text_area("Text", "Please take your medicine twice a day after food.")
    target = c2.selectbox("Translate to", [k for k in LANGUAGES if k != "en"] + ["en"], format_func=lambda k: LANGUAGES[k])
    if st.button("Translate", key="tr"):
        run(lambda: nt.translate(src_text, target=target),
            f'nt.translate({src_text!r}, target={target!r})')

with tab_lid:
    t = st.text_area("Text", "How far, I don reach house.")
    if st.button("Detect", key="lid"):
        run(lambda: f"{nt.detect_language(t)} ({LANGUAGES.get(nt.detect_language(t), '?')})",
            f'nt.detect_language({t!r})')

with tab_cls:
    t = st.text_area("Text", "Dem never bring light for three days now, the transformer don spoil.")
    labels = st.text_input("Labels (comma separated)", "electricity, water, roads, security, health")
    if st.button("Classify", key="cls"):
        labs = [l.strip() for l in labels.split(",") if l.strip()]
        run(lambda: nt.classify(t, labs), f'nt.classify({t!r}, {labs!r})')
