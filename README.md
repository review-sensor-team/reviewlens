# reviewlens

ReviewLens는 쇼핑몰 리뷰를 기반으로
**구매 후회를 줄이기 위한 대화형 리뷰 분석 챗봇**입니다.

핵심 아이디어는 단순 요약이 아니라,
사용자의 우려를 좁혀가며 질문하고,
필요한 시점에만 LLM으로 정리된 답변을 제공하는 것입니다.


Minimal workspace scaffold for the reviewlens project.

This repository contains two top-level folders:
- `backend/`: minimal Python FastAPI backend scaffold (example).
- `frontend/`: placeholder for a frontend app (choose React/Next/Vue/etc.).
- `docs/`: project documentation.

Next steps
- Decide frontend stack (React / Next.js / Vue / Svelte) and I will scaffold it.
- If you prefer a different backend (Flask / Django / FastAPI), tell me and I will switch.

Quick start (backend example)

1. Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install backend deps and run:

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```
