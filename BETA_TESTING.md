# N-ATLAS Kit — Beta Tester Guide (≈20 minutes)

Thank you for testing!

**Easiest way (no install, ~10 min):** open the
[Colab notebook](https://colab.research.google.com/github/ADEYEMIjamiu/natlas-kit/blob/main/notebooks/NATLAS_Kit_Beta_Test.ipynb),
paste the endpoint + API key the team sent you, run the cells top to bottom, and screenshot the summary at the end.

**Full local install** (if you prefer) is below.

## 1. Install (5 min)
```bash
git clone https://github.com/ADEYEMIjamiu/natlas-kit && cd natlas-kit
python3 -m pip install -e ".[server,demo]"
```
Model backend: either run N-ATLAS locally (LM Studio + `bash setup_model.sh`, needs ~8 GB RAM),
or use the shared test endpoint the team sends you:
```bash
export NATLAS_BASE_URL=<endpoint we send you>
```

## 2. Tasks (10 min). Note the time and any errors.
1. `natlas doctor`
2. `natlas translate "Where is the nearest pharmacy?" --to yo` (also try `ha`, `ig`)
3. `natlas scam "<paste a real suspicious SMS you have received>"`
4. In Python:
   ```python
   from natlas_kit import NAtlas
   nt = NAtlas()
   print(nt.chat("Explain inflation simply in Pidgin"))
   ```
5. `streamlit run apps/scam_checker/app.py` → check 3 messages and press 👍/👎.

## 3. Feedback form
| Question | Answer |
|---|---|
| Name, city, role | |
| OS & backend used | |
| Minutes from clone to first working N-ATLAS response | |
| Which tasks worked? (1–5) | |
| Errors / confusing steps | |
| Ease of use (1–5) | |
| Would you use the kit in a real project? Why? | |
| One feature you'd add | |
| May we quote you and list your name as a beta tester? (yes/no) | |

Send the completed table (or a screenshot) to the team lead.
