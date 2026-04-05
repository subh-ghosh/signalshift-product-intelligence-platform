# SignalShift: App Review NLP Analysis

SignalShift is a Data Science project designed to analyze app reviews and automatically surface the most pressing negative issues. It leverages Natural Language Processing (NLP) to parse feedback from the Google Play Store (via Kaggle or CSV), categorize the issues using machine learning, and compute aggregate sentiment metrics.

## Features
- **Data Sync:** Instantly imports app review datasets from Kaggle or CSVs for analysis.
- **Top Negative Issues:** Synthesizes feedback to surface critical negative experiences and bugs.
- **App Rating:** Computes an aggregate app rating and provides a high-level feedback metric over time.

## Tech Stack
- **Machine Learning:** Scikit-learn (Bi-gram TF-IDF + Logistic Regression) and SentenceTransformers (MiniLM issue classification)
- **Backend:** Python, FastAPI, Pandas
- **Frontend:** React, Vite, Tailwind CSS

## Setup Intructions

### 1. Backend Service
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2. Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```

Navigate to `http://localhost:5174` (or the respective Vite port) to interact with the dashboard.
