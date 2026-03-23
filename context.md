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
- [x] Regression coverage added for backend settings parsing and pipeline CLI entrypoints
- [x] Clerk-aware frontend providers, session context, SWR data hooks, and middleware route protection in `frontend/components/providers`, `frontend/context`, `frontend/lib/hooks.ts`, and `frontend/middleware.ts`
- [x] Backend Clerk JWT middleware with public `/api/v1/health` endpoint in `backend/middleware/auth.py`
- [x] Frontend login flow updated to render Clerk Sign-In when env keys are present and a local-development guidance screen when they are not
- [x] Frontend dashboard, analytics, and forecast pages now consume typed SWR hooks instead of page-local fetch logic
- [x] Health checks now target `/api/v1/health` in both root and `infra/` Compose definitions
- [x] Backend persistence migrated to async SQLAlchemy sessions in `backend/services/db_service.py`, `backend/dependencies.py`, and the API routers
- [x] Backend Redis cache migrated to async `redis.asyncio` usage in `backend/services/cache_service.py`
- [x] Forecast generation path now awaits the async persistence layer end to end in `backend/services/forecast_service.py`
- [x] Pipeline PostgreSQL writes now use direct SQL through `pipeline/tasks/load.py` + `pipeline/tasks/database.py`
- [x] Pipeline alert refresh now reads PostgreSQL directly and stores JSON in Redis from `pipeline/flows/alert_flow.py`
- [x] Additional regression coverage added for async persistence contracts and raw SQL alert defaults
- [x] Full Docker Compose stack verified locally: backend healthy, frontend serving, pipeline exits `0`

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
- Inventory alert inserts must set `acknowledged = false` explicitly when bypassing the ORM with raw SQL
- Next.js remains pinned to the latest available 14.x release for this requirement, even though npm audit recommends a major upgrade beyond 14 to fully clear current upstream advisories
- Local Docker Compose currently uses `postgres:16-alpine` to stay compatible with the existing local volume data; moving back to PostgreSQL 15 locally would require a deliberate volume reset or migration

## Current task for this session
Async backend persistence and direct pipeline write migrations are complete. Next recommended task: rebuild the backend/pipeline images once external registry access is available so the updated Prefect 2.x pin in `backend/requirements.txt` is exercised by a fresh Docker image build, then rerun the full root `docker-compose up` verification path.

---

### The "Handoff Prompt" - use this to start every new session

```text
Here is my project context: [paste context.md]

Here are the relevant existing files Codex needs to be aware of:
- [paste backend/models/schemas.py]
- [paste backend/services/db_service.py]
- [paste backend/services/cache_service.py]
- [paste pipeline/tasks/database.py]
- [paste pipeline/tasks/load.py]
- [paste backend/routers/forecast.py]
- [paste backend/ml/predict.py]
- [paste frontend/lib/api.ts]

Current task: [describe the next concrete feature, bugfix, or deployment hardening task for this session]

Follow all conventions already established in the existing files above.
Do not ask clarifying questions. Generate production-ready code now.
```
