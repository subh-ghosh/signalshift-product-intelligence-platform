## Backend Blueprint

The backend is a FastAPI service that exposes multi-tenant ingestion, scoring, and alerting endpoints.

### Layout
- `app/api/` – routers per bounded context (ingestion, scoring, dashboards, alerts).
- `app/services/` – domain logic: ingestion coordinator, priority scoring, anomaly detection, AI summary builder.
- `app/models/` – SQLAlchemy models, DTOs, and tenant-specific schemas.
- `app/workers/` – background workers (Redis Queue, Kafka consumers) plus job definitions and retry policies.
- `app/core/` – shared infrastructure: configuration loader, database session, auth, logging, metrics.
- `tests/` – pytest suite.
- `scripts/` – tooling scripts (seed tenants, run migrations).

### Development
1. Create a `.env` from `.env.example` with database, redis, and jwt secrets.
2. Run migrations via `alembic upgrade head`.
3. Start the API with `uvicorn app.api.main:app --reload`.
