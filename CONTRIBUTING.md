# Contributing to N-ATLAS Kit

Thank you for helping Nigerian developers build on N-ATLAS! 🇳🇬

## Ways to contribute
- **Language data**: add or correct Yoruba, Hausa, Igbo or Pidgin examples in `natlas_kit/eval/data/*.jsonl` (one JSON object per line). Native-speaker reviews are especially welcome.
- **Prompts**: improve templates in `natlas_kit/prompts.py`. Please include before/after `natlas eval` scores in your PR.
- **New tasks**: add an SDK method plus a matching eval task and test.
- **Bugs and docs**: open an issue with steps to reproduce, your OS and your N-ATLAS backend (LM Studio, llama.cpp, vLLM, etc.).

## Development setup
```bash
git clone https://github.com/ADEYEMIjamiu/natlas-kit && cd natlas-kit
python3 -m pip install -e ".[server,demo,dev]"
pytest            # offline tests, no model needed
natlas doctor     # checks your N-ATLAS server
```

## Pull request checklist
- [ ] `pytest` passes
- [ ] New behaviour has a test
- [ ] If you changed prompts or data, include `natlas eval` results (seed **and** holdout sets)
- [ ] Never tune prompts on `scam_holdout.jsonl`. It is the honest test set.

## Code of conduct
Be respectful and patient. Many contributors are first-time open-source developers.
