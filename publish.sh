#!/bin/bash
# Publish N-ATLAS Kit to GitHub as a public repo (run once)
set -e
cd "$(dirname "$0")"
command -v gh >/dev/null || { echo "Install GitHub CLI first: https://cli.github.com"; exit 1; }
gh auth status >/dev/null 2>&1 || gh auth login --web --git-protocol https
[ -d .git ] || git init -b main
git add -A
if git ls-files --error-unmatch .env >/dev/null 2>&1; then echo "STOP: .env is tracked"; exit 1; fi
git -c user.name="Adeyemi Jamiu Adegbenro" -c user.email="speeditdg@gmail.com" commit -m "N-ATLAS Kit v0.1.0: SDK, CLI, REST API, eval harness, Ṣọ́ra reference app" || true
if ! git remote | grep -q origin; then
  gh repo create natlas-kit --public --source . --remote origin --push \
    --description "Developer toolkit for N-ATLAS, Nigeria's multilingual LLM: SDK, CLI, REST API, eval harness"
else
  git push -u origin main
fi
gh repo view --web
echo "PUBLISHED: $(gh repo view --json url -q .url)"
