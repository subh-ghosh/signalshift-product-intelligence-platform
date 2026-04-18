## ML Folder Guide

This folder contains model utilities and retraining scripts.

### Structure
- `core/` - shared ML utilities used in runtime and training.
- `pipeline/` - numbered retraining scripts.
- `testing/` - standalone scripts for quick validation/demo.

### Core Utilities
- `core/text_cleaner.py`
  - Normalizes text (lowercase, URL/symbol cleanup, lemmatization, stopword removal).
- `core/spam_filter.py`
  - Filters low-quality reviews (language, length, repetitiveness heuristics).
- `core/issue_labeler.py`
  - Maps topic keywords to canonical issue labels via MiniLM semantic similarity.

### Pipeline Order
Run from `backend/`:

1. `python ml/pipeline/01_preprocessing.py`
- Reads `data/training/raw/all_combined.csv`
- Writes `data/training/processed/cleaned_all_combined.csv`

2. `python ml/pipeline/02_train_sentiment_model.py`
- Trains sentiment model with TF-IDF + LogisticRegression
- Writes `models/tfidf_vectorizer.joblib`
- Writes `models/sentiment_model.joblib`

3. `python ml/pipeline/03_train_nmf_topic_model.py`
- Trains NMF topic model on negative reviews only
- Writes `models/nmf_vectorizer.joblib`
- Writes `models/nmf_model.joblib`

4. `python ml/pipeline/04_finetune_encoder.py` (optional)
- Reads `data/training/labeled/review_labels.csv`
- Fine-tunes MiniLM using triplet loss
- Writes `models/finetuned_encoder/`
- If `data/training/labeled/review_labels.csv` is missing, step 04 auto-generates it from
  `data/testing/processed/review_classifications.csv` (confidence-filtered).
- Enforces minimum dataset quality (rows/classes) before training.
- Exports `evaluation_report.json` with baseline vs fine-tuned holdout metrics.

### Runtime vs Training Data
- Training scripts only use `data/training/*`.
- Dashboard/runtime analysis uses `data/testing/*` and API ingestion routes.
- Keep these datasets separate to avoid leakage and accidental retraining on inference outputs.

### Labeled Data For Step 04
- Place supervised labels in `data/training/labeled/review_labels.csv`.
- Required columns (aliases supported):
  - text: `review` or `text` or `content`
  - label: `category` or `label` or `issue_label`
- You can skip manual creation initially: step 04 will bootstrap this file automatically
  from runtime classifications if available.

### Runtime Encoder Selection
- Backend runtime will auto-load `models/finetuned_encoder/` when present.
- If not present, it falls back to base `all-MiniLM-L6-v2`.

### Standalone Testing
`testing/top_issues_standalone.py` can run issue extraction directly from a CSV without starting backend or frontend.
