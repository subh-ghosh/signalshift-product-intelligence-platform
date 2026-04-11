"""Shared helpers for the numbered pipeline scripts.

Purpose: keep 01/02/03/04 thin and avoid duplicating paths, dataset validation,
and model IO.

This module is intentionally dependency-light and script-friendly (importable
when running `python backend/ml/pipeline/0X_*.py`).
"""

from __future__ import annotations

import os

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRAINING_CLEAN_CSV = os.path.join(BASE_DIR, "data", "training", "processed", "cleaned_all_combined.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")


def ensure_training_dataset(path: str) -> None:
    normalized = os.path.abspath(path).lower()
    blocked_names = {
        "uploaded_reviews.csv",
        "review_classifications.csv",
        "topic_analysis.csv",
    }
    if os.path.basename(normalized) in blocked_names:
        raise ValueError(
            "Inference/output CSVs cannot be used for training. "
            "Use the curated training dataset such as cleaned_all_combined.csv."
        )


def load_cleaned_dataset(path: str = TRAINING_CLEAN_CSV) -> pd.DataFrame:
    ensure_training_dataset(path)
    df = pd.read_csv(path)
    print("Dataset loaded:", df.shape)

    df = df.dropna(subset=["cleaned_content"]).copy()
    df["cleaned_content"] = df["cleaned_content"].astype(str)

    print("Dataset after validation:", df.shape)
    return df


def build_tfidf_vectorizer(*, max_features: int = 10000, ngram_range: tuple[int, int] = (1, 2)) -> TfidfVectorizer:
    return TfidfVectorizer(max_features=max_features, ngram_range=ngram_range)


def fit_tfidf_vectorizer(
    df: pd.DataFrame,
    *,
    max_features: int = 10000,
    ngram_range: tuple[int, int] = (1, 2),
) -> tuple[TfidfVectorizer, object]:
    """Fits TF-IDF on df['cleaned_content'] and returns (vectorizer, X)."""
    print("\nCreating TF-IDF features...")
    vectorizer = build_tfidf_vectorizer(max_features=max_features, ngram_range=ngram_range)
    X = vectorizer.fit_transform(df["cleaned_content"])
    print("TF-IDF matrix shape:", X.shape)
    return vectorizer, X


def save_vectorizer(vectorizer: TfidfVectorizer, model_dir: str = MODEL_DIR) -> str:
    os.makedirs(model_dir, exist_ok=True)
    path = os.path.join(model_dir, "tfidf_vectorizer.joblib")
    print("\nSaving vectorizer...")
    joblib.dump(vectorizer, path)
    print("Vectorizer saved successfully.")
    return path


def load_vectorizer(model_dir: str = MODEL_DIR) -> TfidfVectorizer:
    path = os.path.join(model_dir, "tfidf_vectorizer.joblib")
    if not os.path.exists(path):
        raise FileNotFoundError(
            "TF-IDF vectorizer not found. Run 02_train_sentiment_model.py to create "
            "models/tfidf_vectorizer.joblib (and sentiment_model.joblib)."
        )
    return joblib.load(path)


def save_sentiment_model(model, model_dir: str = MODEL_DIR) -> str:
    os.makedirs(model_dir, exist_ok=True)
    path = os.path.join(model_dir, "sentiment_model.joblib")
    joblib.dump(model, path)
    print("Sentiment model saved successfully.")
    return path
