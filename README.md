# SignalShift Platform

SignalShift is a Product Intelligence prototype for transforming unstructured customer feedback into actionable insights (sentiment, topics, and issue labels) with a dashboard.

## Overview
- **Problem:** Large volumes of feedback (reviews, tickets, surveys) are currently analyzed manually, causing slow detection of regressions, poor prioritization, and missing executive summaries.
- **Solution:** Ingest reviews, run ML analysis, and visualize KPIs + top issues.
- **Primary Stack (in this repo):** FastAPI (backend) + React (Vite) (frontend) + scikit-learn / SentenceTransformers / spaCy (ML).

## Repository Layout
- `backend/` – FastAPI API (`backend/app`) plus ML runtime + training scripts (`backend/ml`).
- `frontend/` – React + Vite dashboard.
- `research_docs/` – Research and benchmarking writeups.

## Getting Started
1. Backend:
	- `pip install -r backend/requirements.txt`
	- `python -m spacy download en_core_web_sm`
	- `cd backend && uvicorn app.main:app --reload --port 8002`
2. Frontend:
	- `cd frontend && npm install`
	- `npm run dev`

The frontend talks to the backend at `VITE_API_URL` (defaults to `http://127.0.0.1:8002`).

## Contributing
Keep changes minimal and consistent with the DS-style layout conventions (canonical ML pipeline scripts under `backend/ml/pipeline`).
