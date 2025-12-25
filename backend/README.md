FastAPI backend (placeholder)

Quick start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

Health: `http://localhost:8000/health`
Reviews: `http://localhost:8000/reviews`
