## Backend Blueprint

The backend is a FastAPI service that exposes ingestion and dashboard endpoints and runs the local ML runtime (sentiment, topics, and issue labeling).

### Layout
- `app/api/` - API routes.
- `app/services/` - CSV processing, ML service, syncing/reporting helpers.
- `ml/` - ML runtime + pipeline tooling.
- `models/` - runtime artifacts (vectorizers/models).
- `data/training/` - curated training data for retraining.
- `data/testing/` - runtime/dashboard input + processed analytics outputs.

### Data Separation (Important)
SignalShift intentionally separates model training data from dashboard/runtime data:

1. Training path
- Source: `data/training/raw/all_combined.csv`
- Processed: `data/training/processed/cleaned_all_combined.csv`
- Labeled (optional for step 04): `data/training/labeled/review_labels.csv`
- Used by pipeline scripts in `ml/pipeline/`
- Produces model artifacts in `models/`

2. Runtime/dashboard path
- Input: uploaded CSVs or Kaggle sync data
- Raw runtime data: `data/testing/raw/`
- Processed analytics outputs: `data/testing/processed/`
- Used by dashboard endpoints under `app/api/routes.py`

The pipeline helpers in `ml/pipeline/pipeline_common.py` also block common inference/output CSV files from being used as training input.

### Retraining Steps
Run from `backend/`:

1. `python ml/pipeline/01_preprocessing.py`
2. `python ml/pipeline/02_train_sentiment_model.py`
3. `python ml/pipeline/03_train_nmf_topic_model.py`
4. `python ml/pipeline/04_finetune_encoder.py` (optional, requires labeled data)
5. Restart API so models are reloaded.

When available, runtime automatically prefers `models/finetuned_encoder/` and falls
back to base `all-MiniLM-L6-v2` otherwise.

### Runtime/Dashboard Flow
1. Upload reviews (`/upload-reviews`) or sync (`/sync/kaggle`).
2. Backend runs background sentiment + topic analysis.
3. Analytics CSVs are written to `data/testing/processed/`.
4. Dashboard endpoints (`/dashboard/*`) read these outputs.

### Development
1. Install dependencies: `pip install -r requirements.txt`
2. Install spaCy model (needed by preprocessing): `python -m spacy download en_core_web_sm`
3. Start the API:
- From `backend/`: `uvicorn app.main:app --reload --port 8002`
