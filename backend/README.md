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
This repo is intended to run in a local virtual environment (`.venv`).
On some Linux distros, the system Python may not include `pip` or common ML
packages, so using `.venv` avoids “missing pandas/sklearn” errors.

1. Create and activate a virtual environment:
	- `python3 -m venv .venv`
	- `source .venv/bin/activate`
2. Install dependencies:
	- `python -m pip install -r requirements.txt`

3. (Optional) Train/rebuild ML artifacts (writes to `backend/models/`):
	- `python -u ml/pipeline/01_preprocessing.py`
	- `python -u ml/pipeline/02_vectorization.py`
	- `python -u ml/pipeline/03_train_sentiment_model.py`
	- `python -u ml/pipeline/04_create_issue_embeddings.py`

4. Start the API:
	- `uvicorn app.main:app --reload --port 8002`
