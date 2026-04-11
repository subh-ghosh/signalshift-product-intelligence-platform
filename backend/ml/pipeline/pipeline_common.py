"""Shared helpers for the ML training pipeline scripts.

Design goals:
- Keep step scripts thin and readable.
- Centralize dataset paths + artifact IO.
- Avoid accidentally training on inference/output CSVs.

Run scripts from repo root, e.g.:
  python3 backend/ml/pipeline/01_preprocess_training_reviews.py
"""

from __future__ import annotations

import os

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


# This file lives at backend/ml/pipeline/pipeline_common.py
# backend_dir = backend/
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TRAINING_RAW_CSV = os.path.join(BACKEND_DIR, "data", "training", "raw", "all_combined.csv")
TRAINING_CLEAN_CSV = os.path.join(
    BACKEND_DIR, "data", "training", "processed", "cleaned_all_combined.csv"
)

MODEL_DIR = os.path.join(BACKEND_DIR, "models")

# Align with the runtime service (subh branch uses v2 artifacts)
VECTORIZER_PATH = os.path.join(MODEL_DIR, "tfidf_vectorizer_v2.joblib")
SENTIMENT_MODEL_PATH = os.path.join(MODEL_DIR, "sentiment_model_v2.joblib")


def ensure_training_dataset(path: str) -> None:
    normalized_name = os.path.basename(os.path.abspath(path)).lower()
    blocked_names = {
        "uploaded_reviews.csv",
        "cleaned_reviews.csv",
        "review_classifications.csv",
        "topic_analysis.csv",
        "topic_timeseries.csv",
    }
    if normalized_name in blocked_names:
        raise ValueError(
            "Inference/output CSVs cannot be used for training. "
            "Use the curated training dataset under backend/data/training/."
        )


def load_raw_dataset(path: str = TRAINING_RAW_CSV) -> pd.DataFrame:
    ensure_training_dataset(path)
    df = pd.read_csv(path)
    if "content" not in df.columns:
        raise ValueError("Training raw CSV must contain a 'content' column.")
    return df


def save_cleaned_dataset(df: pd.DataFrame, path: str = TRAINING_CLEAN_CSV) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    return path


def load_cleaned_dataset(path: str = TRAINING_CLEAN_CSV) -> pd.DataFrame:
    ensure_training_dataset(path)
    df = pd.read_csv(path)
    if "cleaned_content" not in df.columns:
        raise ValueError(
            "Cleaned training CSV must contain 'cleaned_content'. "
            "Run 01_preprocess_training_reviews.py first."
        )
    df = df.dropna(subset=["cleaned_content"]).copy()
    df["cleaned_content"] = df["cleaned_content"].astype(str)
    return df


def build_tfidf_vectorizer(
    *,
    max_features: int = 10000,
    ngram_range: tuple[int, int] = (1, 2),
) -> TfidfVectorizer:
    return TfidfVectorizer(max_features=max_features, ngram_range=ngram_range)


def fit_tfidf_vectorizer(
    df: pd.DataFrame,
    *,
    max_features: int = 10000,
    ngram_range: tuple[int, int] = (1, 2),
) -> tuple[TfidfVectorizer, object]:
    vectorizer = build_tfidf_vectorizer(max_features=max_features, ngram_range=ngram_range)
    X = vectorizer.fit_transform(df["cleaned_content"])
    return vectorizer, X


def save_vectorizer(vectorizer: TfidfVectorizer, path: str = VECTORIZER_PATH) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(vectorizer, path)
    return path


def load_vectorizer(path: str = VECTORIZER_PATH) -> TfidfVectorizer:
    if not os.path.exists(path):
        raise FileNotFoundError(
            "TF-IDF vectorizer not found. Run 02_fit_tfidf_vectorizer.py to create it."
        )
    return joblib.load(path)


def save_sentiment_model(model, path: str = SENTIMENT_MODEL_PATH) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)
    return path
