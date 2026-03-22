# SupplyIQ

SupplyIQ is an AI-powered supply chain intelligence platform with a four-layer architecture:

`Prefect Pipeline -> PostgreSQL + Redis -> FastAPI Backend -> Next.js 14 Frontend`

## Run

From the repo root:

```bash
docker-compose up
```

Frontend: `http://localhost:3000`

Backend API: `http://localhost:8000/api/v1`

## Architecture

- `frontend/` contains the Next.js 14 App Router application
- `backend/` contains the FastAPI server, SQLAlchemy models, services, and ML inference layer
- `pipeline/` contains Prefect flows and tasks for ingestion and alert refresh
- `infra/` contains Dockerfiles, Compose config, and database initialization SQL

## ML Workflow

- `backend/ml/train.py` generates the serialized joblib model artifact during backend image build
- `backend/ml/predict.py` contains the inference-time feature and forecast logic
- The FastAPI app loads the model artifact once at startup and never retrains on request
