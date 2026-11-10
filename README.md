# Kandumas

IT3004 Capstone Project (Cyryx College) -- a web system that forecasts Maldivian tuna
catch volumes using machine learning (LSTM + Prophet) trained on real environmental
data (NOAA) and real historical catch data (IOTC), served through a FastAPI backend and
a React dashboard. The name comes from Dhivehi *kandu* (sea) + *mas* (fish).

See `docs/DATA_SOURCES.md` for exactly where every number comes from,
`docs/CRISP-DM.md` for how the ML pipeline maps to the CRISP-DM phases described in
Chapter 1, and `docs/USER_MANUAL.md` for a walkthrough of each screen (the same
guidance is also built into the app itself, on the Help page).

## Stack

- **Frontend:** React (Vite), Chart.js, Leaflet
- **Backend:** FastAPI, SQLAlchemy, Alembic
- **Database:** MySQL
- **ML:** TensorFlow/Keras (LSTM), Prophet, scikit-learn
- **Reports:** reportlab (PDF), CSV
- **Containers:** Docker / Docker Compose

## Project layout

```
backend/    FastAPI app + ML pipeline (ingestion, preprocessing, training, serving)
frontend/   React dashboard
data/       raw (fetched) and processed (feature table) data
docs/       data source documentation, CRISP-DM mapping, user manual
```

## Running it locally (native, no Docker)

Prerequisites: Python 3.11+, Node 18+, and a MySQL server (or run just the `mysql`
service from `docker-compose.yml`: `docker compose up -d mysql`).

1. **Configure environment**
   ```
   cp .env.example .env
   # edit .env if your MySQL host/port/password differ from the defaults
   ```

2. **Backend setup**
   ```
   cd backend
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```

3. **Fetch real data** (see docs/DATA_SOURCES.md -- NOAA's fetch is slow, ~20-25 min)
   ```
   python -m app.ml.ingestion.iotc
   python -m app.ml.ingestion.noaa
   python -m app.ml.pipeline.preprocess
   ```

4. **Database: migrate + seed**
   ```
   python -m alembic upgrade head
   python -m app.ml.pipeline.seed
   ```

5. **Train the models**
   ```
   python -m app.ml.training.train_lstm
   python -m app.ml.training.train_prophet
   python -m app.ml.training.evaluate
   ```

6. **Run the API**
   ```
   python -m uvicorn app.main:app --reload --port 8000
   ```

7. **Frontend**
   ```
   cd ../frontend
   npm install
   npm run dev
   ```
   Open http://localhost:5173. Demo accounts (passwords come from `.env`,
   `DEMO_*_PASSWORD`): `fisherman1`, `officer1`, `admin1`.

## Running it with Docker Compose

```
docker compose up -d mysql          # start the database first
cd backend && python -m alembic upgrade head && python -m app.ml.pipeline.seed
docker compose up -d --build        # backend + frontend
```

The ingestion/training scripts (steps 3 and 5 above) are one-off data-preparation jobs,
not part of the running containers -- run them natively (or `docker compose exec
backend python -m app.ml.ingestion.iotc` etc.) before or after bringing the stack up.
The Admin page's "Refresh Datasets" / "Retrain Model" buttons also trigger them from
inside the running backend container.

## Testing (WBS 4.5, 5.5)

Backend (pytest, against a throwaway SQLite DB -- no MySQL server needed):
```
cd backend
python -m pytest tests -v
```

Frontend (Vitest + React Testing Library):
```
cd frontend
npm run test
```

## Deployment

Not yet wired up -- Railway (backend), Vercel (frontend) and Cloudflare (DNS) are the
next phase, per the Project Management Plan's WBS Phase 6, tasks 6.3-6.5.

## Demo accounts

| Username | Role | Password env var |
|---|---|---|
| fisherman1 | fisherman | `DEMO_FISHERMAN_PASSWORD` |
| officer1 | officer | `DEMO_OFFICER_PASSWORD` |
| admin1 | admin | `DEMO_ADMIN_PASSWORD` |
