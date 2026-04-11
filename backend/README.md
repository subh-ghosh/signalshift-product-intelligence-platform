## Backend Blueprint

The backend is a FastAPI service that exposes ingestion and dashboard endpoints and runs the local ML runtime (sentiment, topics, and issue labeling).

### Layout
- `app/api/` – API routes.
- `app/services/` – CSV processing, ML service, syncing/reporting helpers.
- `ml/` – ML runtime + pipeline tooling.
- `models/` – runtime artifacts (vectorizers/models).

### Development
1. Install dependencies: `pip install -r requirements.txt`
2. Install spaCy model (needed by preprocessing): `python -m spacy download en_core_web_sm`
3. Start the API:
	- From `backend/`: `uvicorn app.main:app --reload --port 8002`
