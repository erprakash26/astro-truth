# AstroTruth

AstroTruth is a Vedic astrology application that computes precise, deterministic
planetary charts (sidereal zodiac, Lahiri ayanamsa, whole-sign houses) and uses
an LLM to interpret the resulting data in plain language — the math and the
narration are kept strictly separate.

## Structure

- `backend/` — Python 3.11 + FastAPI service exposing chart computation and
  interpretation endpoints.
- `frontend/` — React + Vite + Tailwind single-page app.

## Backend setup

```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Frontend setup

```
cd frontend
npm install
npm run dev
```

See `CLAUDE.md` for project conventions.
