# SupplyIQ - Codex Session Context

## What this project is
AI-powered supply chain intelligence platform. Four-layer architecture:
Prefect pipeline -> PostgreSQL + Redis -> FastAPI backend -> Next.js 14 frontend

## What is already built (update this as you go)
- [x] Git repo initialized on `main`
- [x] Next.js 14 App Router frontend in `frontend/app`, `frontend/components`, `frontend/lib`, and `frontend/types`
- [x] FastAPI backend in `backend/main.py` + `backend/routers/*`
- [x] SQLAlchemy ORM models in `backend/models/db_models.py`
- [x] Pydantic request/response models in `backend/models/schemas.py`
- [x] Redis caching service in `backend/services/cache_service.py`
- [x] DB query helpers in `backend/services/db_service.py`
- [x] Model loading + inference logic in `backend/services/forecast_service.py`
- [x] Joblib training/inference scripts in `backend/ml/train.py` and `backend/ml/predict.py`
- [x] PostgreSQL + Redis infra in `infra/docker-compose.yml`
- [x] Prefect pipeline in `pipeline/flows` + `pipeline/tasks`
- [x] Repo-root `docker-compose.yml` preserved for `docker-compose up` from the root
- [x] Backend persistence migrated to async SQLAlchemy sessions in `backend/services/db_service.py`, `backend/dependencies.py`, and the API routers
- [x] Backend Redis cache migrated to async `redis.asyncio` usage in `backend/services/cache_service.py`
- [x] Pipeline PostgreSQL writes now use direct SQL through `pipeline/tasks/load.py`
- [x] Pipeline alert refresh now reads PostgreSQL directly and stores JSON in Redis from `pipeline/flows/alert_flow.py`
- [x] Clerk-aware frontend providers, session context, SWR data hooks, and middleware route protection remain wired for optional auth
- [x] Health checks target `/api/v1/health` in both root and `infra/` Compose definitions
- [x] Exact six-table PostgreSQL schema replacement completed across ORM and bootstrap SQL:
  `products`, `regions`, `inventory_snapshots`, `daily_sales`, `supplier_shipments`, and `forecast_runs`
- [x] Raw bootstrap SQL in `infra/init.sql` now creates `pgcrypto`, the exact tables, the inventory uniqueness rule, and the required indexes
- [x] Backend contracts, routers, and query logic now use `region_id`, latest inventory snapshots, derived stockout alerts, shipment-based supplier analytics, and JSON forecast persistence
- [x] Forecast generation now always produces a 7-day `forecast_json` payload plus `shap_json` feature-contribution metadata
- [x] Pipeline extract/transform/load now seeds only the exact-schema tables required by the new model
- [x] Frontend dashboard, analytics, and forecast screens now render the new inventory, shipment, and forecast JSON shapes
- [x] Regression coverage added for schema metadata, SQL bootstrap contents, async persistence behavior, and pipeline CLI entrypoints
- [x] Frontend lint and production build verified locally after the schema transition
- [x] Full Docker Compose stack verified locally against a fresh isolated volume: backend healthy, frontend serving, postgres healthy, redis running, pipeline exits `0`

## Critical decisions made (don't change these)
- System flow is `Prefect -> PostgreSQL + Redis -> FastAPI -> Next.js`
- Frontend must use Next.js 14 App Router and TypeScript
- Backend must use FastAPI with Pydantic request/response validation
- ML models must be serialized with `joblib` and loaded at startup, never retrained on request
- Environment-specific values belong in `.env` files, not hardcoded into app logic
- Docker Compose remains the primary local run path
- Backend settings must accept plain-string or JSON-array CORS origins from environment variables
- Backend keeps a sync-style PostgreSQL env var and converts it internally to `asyncpg` for SQLAlchemy async sessions
- Docker bootstrap must execute pipeline CLI helpers directly; decorated Prefect flows remain for orchestrated runs
- Pipeline direct DB clients must strip SQLAlchemy driver suffixes before connecting to PostgreSQL
- Clerk auth remains optional in local development until env keys are set; when enabled, frontend middleware and backend bearer-token validation activate together
- Public health and container readiness endpoint is `/api/v1/health`
- Persistent application schema must remain exactly these six tables with no extra persisted tables or columns:
  `products`, `regions`, `inventory_snapshots`, `daily_sales`, `supplier_shipments`, and `forecast_runs`
- Inventory alerts are derived from the latest inventory snapshot versus `products.reorder_point`; they are not stored in a separate table
- Forecast persistence is JSON-first: `forecast_runs.forecast_json` stores the 7-day forecast payload and `forecast_runs.shap_json` stores the top feature contributions
- Supplier analytics are shipment-truthful and aggregate `supplier_shipments` by `supplier_name`
- Root Docker Compose currently uses `postgres:16-alpine`; fresh bootstrap verification was completed with an isolated Compose project so `infra/init.sql` ran from an empty volume
- `prefect==2.20.25` requires `sqlalchemy<2.0.36`, so `backend/requirements.txt` is intentionally pinned to `sqlalchemy==2.0.35`

## ML Model Architecture (confirmed)
- One Prophet model trained per `(product_id, region_id)` pair
- Artifacts: `backend/ml/artifacts/prophet_{product_id}_{region_id}.joblib`
- One XGBoost residual model (global, trained on all product-region data)
- Training window: full 2-year history
- Inference window: last 90 days for feature matrix only
- If prophet artifact missing for a pair -> HTTP 404, don't silently fail

## Current task for this session
Exact-schema replacement is implemented and verified. Next recommended task: add API-level smoke/regression coverage for the live `/inventory`, `/analytics`, and `/forecast` endpoints so the new `region_id` filters, derived alerts, shipment metrics, and JSON forecast payloads are exercised end to end.

## Cleanup rule
No test files should persist between sessions. Run CLEANUP.md prompt before closing every session.

---

### The "Handoff Prompt" - use this to start every new session

```text
Here is my project context: [paste context.md]

Here are the relevant existing files Codex needs to be aware of:
- [paste backend/models/db_models.py]
- [paste backend/models/schemas.py]
- [paste backend/services/db_service.py]
- [paste backend/services/forecast_service.py]
- [paste pipeline/tasks/load.py]
- [paste pipeline/flows/alert_flow.py]
- [paste backend/ml/predict.py]
- [paste frontend/lib/api.ts]
- [paste frontend/types/index.ts]

Current task: [describe the next concrete feature, bugfix, or deployment hardening task for this session]

Follow all conventions already established in the existing files above.
Do not ask clarifying questions. Generate production-ready code now.
```
