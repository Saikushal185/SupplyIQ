# SupplyIQ

SupplyIQ is an ML-powered supply chain intelligence platform. It forecasts product demand seven days ahead using a hybrid model — **Prophet** baselines per product-region pair, a global **XGBoost** residual-correction model, and **SHAP** explainability so every forecast shows *why* the model predicted what it did — and derives stockout alerts, supplier reliability, and regional growth analytics on top of a PostgreSQL + Redis + FastAPI + Next.js stack.

## Architecture

```text
 +--------------------+        +---------------------------+
 |  Seed + Ingestion  |        |  ML Training              |
 |  pipeline/ infra/  +-------->  Prophet per scope        |
 |  synthetic demand  |        |  XGBoost residuals + SHAP |
 +---------+----------+        +-------------+-------------+
           |                                 |
           v                                 v
 +---------+---------------------------------+-------------+
 |                PostgreSQL + Redis                        |
 |  products | regions | daily_sales | inventory_snapshots |
 |  supplier_shipments | forecast_runs | cache             |
 +---------------------------+------------------------------+
                             |
                   +---------v----------+
                   |  FastAPI backend   |
                   |  localhost:8000    |
                   +---------+----------+
                             |
                   +---------v----------+
                   |  Next.js frontend  |
                   |  localhost:3000    |
                   +--------------------+
```

## Quick Start

```bash
docker compose up --build
```

That is the whole setup. On first run the backend automatically:

1. Creates the schema (six tables).
2. Seeds **two years** of synthetic history — 20 products across 4 categories, 5 regions, with realistic seasonality (electronics spike in Nov-Dec, food stays steady) plus supplier shipment records.
3. Trains the forecast models (Prophet per product-region + global XGBoost residual model + SHAP explainer). Expect **2–5 minutes** on the first boot; subsequent starts skip all of this and come up in seconds.

Then open [http://localhost:3000](http://localhost:3000). API docs live at [http://localhost:8000/docs](http://localhost:8000/docs).

To disable the auto-bootstrap (e.g. after the first run), set `BACKEND_AUTO_BOOTSTRAP=false` in a root `.env` file (see `.env.example` — every variable has a working default).

## What to Look At

- **Dashboard** — network-wide inventory positions, 30-day sales trend, low-stock watchlist, and last pipeline run.
- **Analytics** — product sales, inventory turnover, regional revenue growth, and shipment-truthful supplier reliability (on-time rate from `supplier_shipments`).
- **Forecast Studio** — pick any product + region and generate a 7-day demand forecast with confidence bounds, stockout-risk detection against reorder points, and a SHAP panel showing the top feature contributions (weather, traffic, lags, rolling averages).
- **Pipeline Monitor** — status of the most recent data ingestion run.

## Project Layout

```text
backend/    FastAPI app: routers, services, SQLAlchemy models, ML train/predict
frontend/   Next.js 14 App Router UI (TypeScript, Tailwind, ECharts, SWR)
pipeline/   Plain-Python ETL: simulate a day of demand -> validate -> upsert
infra/      init.sql, seed script, Dockerfiles
```

## ML Model Details

- One Prophet model per `(product_id, region_id)` pair, trained on the full 2-year history; artifacts in `backend/ml/artifacts/`.
- One global XGBoost model trained on Prophet residuals with engineered features (`weather_temp`, `traffic_index`, day-of-week, weekend flag, month, 7-day rolling average, lag-1, lag-7).
- SHAP TreeExplainer surfaces per-forecast feature contributions, persisted as `shap_json` alongside each `forecast_runs` row.
- Models are loaded from disk at request time — never retrained per request. Missing per-scope models return HTTP 404 with a clear message.

## Running Pieces Manually

```bash
# Re-seed (idempotent upserts)
docker compose exec backend python /app/infra/seed.py

# Re-train models
docker compose exec backend python /app/backend/ml/train.py

# Simulate one more day of demand data
docker compose exec backend python -m pipeline.flows.ingestion_flow

# Run the backend test suite
docker compose exec backend python -m unittest discover -s /app/backend/tests -t /app
```

## Local Development Without Docker

Backend: `pip install -r backend/requirements.txt`, set `BACKEND_DATABASE_URL` / `BACKEND_REDIS_URL` (see `backend/.env.example`), then `uvicorn main:app --reload` from `backend/` with `PYTHONPATH` pointing at the repo root.

Frontend: `cd frontend && npm install && npm run dev` with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1` in `frontend/.env.local`.
