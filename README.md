# SellerPulse — Seller Operations & Payout Intelligence

A local-first candidate project. This repository is a starter scaffold; review and validate it before submission.

## Stack
- Frontend: React + TypeScript + Vite + Recharts + Lucide
- Backend: FastAPI
- Storage: SQLite
- Tests: Pytest

## Run backend
Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

## Run frontend (second terminal)
Node.js 20+ recommended.

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL (normally http://localhost:5173). API docs are at http://127.0.0.1:8000/docs.

## Tests
```bash
pytest
```

## Before submission
- Complete and validate the requested 2,000 sellers / 20,000 listings / 100,000 orders / 10,000 disputes generator.
- Implement and test all five required anomaly scenarios.
- Compare deterministic output checksums across two runs.
- Keep ground truth separate from detector input features.
- Record all AI prompts and explain your own review/validation.
- Use synthetic data only; never commit secrets or personal data.
