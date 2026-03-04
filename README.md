# SignalShift Platform

SignalShift is a production-grade Product Intelligence system for transforming unstructured customer feedback into prioritized, actionable insights. This repository captures the core architecture, teams, and tooling needed to deliver the 2026-standard platform described in the Product & Engineering Master Document.

## Overview
- **Problem:** Large volumes of feedback (reviews, tickets, surveys) are currently analyzed manually, causing slow detection of regressions, poor prioritization, and missing executive summaries.
- **Solution:** A multi-tenant SaaS that ingests feedback, applies NLP + analytics, scores impact, detects anomalies, and shares insights via dashboards and alerts.
- **Primary Stack:** Next.js 14 + TypeScript (frontend), FastAPI (backend), PostgreSQL, Redis, Dockerized services, and ML + pipeline tooling (Hugging Face, scikit-learn, BERTopic, Kafka in Phase 2).

## Repository Layout
- `backend/` – FastAPI service structured around API, services, models, and analytics helpers.
- `frontend/` – Next.js 14 workspace with layouts, shared components, and data layer to consume the backend APIs.
- `docs/` – Architecture, deployment, and onboarding docs keyed to the 2026 standard.
- `infra/` – IaC helpers (Docker, Terraform templates, pipeline configs) to align with production expectations.
- `data/` – Data pipeline code, preprocessing scripts, and sample schema definitions for ingestion, NLP, and scoring.
- `observability/` – Shared logging, metrics, tracing, and alerting config.
- `config/` – Environment templates, secrets vault reference, and rate-limiting/tenant isolation policy files.

## Getting Started
1. Read `docs/architecture.md` for the system blueprint and component responsibilities.
2. Install backend dependencies via `pip install -r backend/requirements.txt` (or `poetry install`) and initialize the database for the relevant tenant.
3. Spin up the frontend with `pnpm install && pnpm dev` from `frontend/`.
4. Use `infra/docker-compose.dev.yml` to run Redis, PostgreSQL, and other services locally mirroring the production stack.

## Contributing
Adhere to the engineering principles outlined in `docs/engineering-principles.md`: multi-tenant isolation, async-first, event-driven, scalable, structured logging, and idempotent ingestion. Every feature should have a matching test or contract and documentation that explains usage and failure handling.
