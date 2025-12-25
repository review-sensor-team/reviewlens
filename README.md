# reviewlens

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
