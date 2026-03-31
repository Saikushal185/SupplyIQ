# SupplyIQ

SupplyIQ is a supply chain intelligence platform with a FastAPI backend, a Next.js frontend, and a Prefect ingestion pipeline that refreshes operational demand signals every day at `02:00 UTC`.

## Architecture

```text
                    +---------------------------+
                    |  Prefect Ingestion Flow   |
                    |  02:00 UTC daily          |
                    +------------+--------------+
                                 |
         +-----------------------+------------------------+
         |                                                |
 +-------v--------+                               +-------v--------+
 |  OpenWeather   |                               |  Resend Alerts |
 |  API           |                               |  Low-stock mail|
 +-------+--------+                               +-------+--------+
         |                                                ^
         v                                                |
+--------+------------------------------------------------+--------+
|                    PostgreSQL + Redis                            |
|  products | regions | daily_sales | inventory_snapshots | cache  |
+--------+------------------------------------------------+--------+
         |                                                |
 +-------v--------+                               +-------v--------+
 |  FastAPI API   |                               |  ML Training   |
 |  localhost:8000|                               |  backend/ml    |
 +-------+--------+                               +----------------+
         |
 +-------v--------+
 | Next.js App    |
 | localhost:3000 |
 +----------------+
```

## Quick Start

1. Clone the repo.
2. Copy the root env file: `cp .env.example .env`
3. Fill in backend secrets in [backend/.env](/C:/Users/saiku/OneDrive/Desktop/Projects/SupplyIQ/backend/.env) and frontend secrets in [frontend/.env.local](/C:/Users/saiku/OneDrive/Desktop/Projects/SupplyIQ/frontend/.env.local)
4. Start infrastructure and app containers: `docker-compose up --build`
5. Seed historical data once: `docker-compose run backend python /app/infra/seed.py`
6. Train the forecast model: `docker-compose run backend python /app/backend/ml/train.py`
7. Open `http://localhost:3000`

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Environment Variables

Frontend in [frontend/.env.local](/C:/Users/saiku/OneDrive/Desktop/Projects/SupplyIQ/frontend/.env.local):

- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`
- `NEXT_PUBLIC_API_URL`

Backend in [backend/.env](/C:/Users/saiku/OneDrive/Desktop/Projects/SupplyIQ/backend/.env):

- `DATABASE_URL`
- `REDIS_URL`
- `CLERK_SECRET_KEY`
- `OPENWEATHERMAP_API_KEY`
- `RESEND_API_KEY`
- `PREFECT_API_KEY`
- `ALERT_EMAIL_FROM`

## Pipeline Overview

- `pipeline/flows/ingestion_flow.py` runs extract, transform, and load.
- `pipeline/tasks/extract.py` simulates daily product-by-region demand with numpy noise, seasonal category curves, real OpenWeatherMap temperatures, and traffic scaling by execution hour.
- `pipeline/tasks/transform.py` validates rows with Pydantic, rejects invalid sales, computes revenue, and flags below-reorder inventory positions.
- `pipeline/tasks/load.py` upserts `daily_sales`, upserts `inventory_snapshots`, and invalidates analytics cache keys in Redis.
- `pipeline/flows/alert_flow.py` sends rate-limited low-inventory emails through Resend.

## Seeding And Training

- [infra/seed.py](/C:/Users/saiku/OneDrive/Desktop/Projects/SupplyIQ/infra/seed.py) generates two years of realistic history for 20 products across 4 categories and 5 regions.
- Electronics receive a Nov-Dec demand lift; food stays comparatively steady year-round.
- The seed script is idempotent through `ON CONFLICT DO UPDATE`, so reruns refresh the same historical windows instead of duplicating rows.
- `backend/ml/train.py` trains Prophet per product-region scope and XGBoost residual corrections from `daily_sales`.

## Deployment Guide

### Vercel Frontend

1. Create a new Vercel project and point it at the `frontend/` app.
2. Set `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, and `NEXT_PUBLIC_API_URL`.
3. Set the build command to `npm run build` and the output to Next.js defaults.
4. Deploy and verify the app can reach the Railway backend URL.

### Railway Backend

1. Create a Railway project for the backend service and PostgreSQL/Redis.
2. Deploy the repo with [infra/Dockerfile.backend](/C:/Users/saiku/OneDrive/Desktop/Projects/SupplyIQ/infra/Dockerfile.backend).
3. Configure `DATABASE_URL`, `REDIS_URL`, `OPENWEATHERMAP_API_KEY`, `RESEND_API_KEY`, `PREFECT_API_KEY`, and `ALERT_EMAIL_FROM`.
4. Run `python /app/infra/seed.py` once, then `python /app/backend/ml/train.py`.
5. Point Vercel `NEXT_PUBLIC_API_URL` to the Railway FastAPI base URL.
