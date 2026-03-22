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
- [ ] Runtime auth enforcement - NOT started (login surface is scaffolded, provider wiring is pending)
- [x] Full Docker Compose stack verified locally: backend healthy, frontend serving, pipeline exits `0`

## Critical decisions made (don't change these)
- System flow is `Prefect -> PostgreSQL + Redis -> FastAPI -> Next.js`
- Frontend must use Next.js 14 App Router and TypeScript
- Backend must use FastAPI with Pydantic request/response validation
- ML models must be serialized with `joblib` and loaded at startup, never retrained on request
- Environment-specific values belong in `.env` files, not hardcoded into app logic
- Docker Compose remains the primary local run path
- Backend settings must accept plain-string or JSON-array CORS origins from environment variables
- Docker bootstrap must execute pipeline CLI helpers directly; decorated Prefect flows remain for orchestrated runs
- Next.js remains pinned to the latest available 14.x release for this requirement, even though npm audit recommends a major upgrade beyond 14 to fully clear current upstream advisories

## Current task for this session
Project bootstrapping and local Docker run are complete. Next recommended task: wire real auth enforcement and expand automated test coverage beyond the current regression tests.

---

### The "Handoff Prompt" - use this to start every new session

```text
Here is my project context: [paste context.md]

Here are the relevant existing files Codex needs to be aware of:
- [paste backend/models/schemas.py]
- [paste backend/routers/forecast.py]
- [paste backend/ml/predict.py]
- [paste frontend/lib/api.ts]

Current task: [describe the exact feature, bugfix, or refactor for this session]

Follow all conventions already established in the existing files above.
Do not ask clarifying questions. Generate production-ready code now.
```
