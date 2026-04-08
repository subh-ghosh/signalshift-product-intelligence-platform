"""Load sentiment model artifacts (vectorizer + classifier)."""

from __future__ import annotations

import os

import joblib


def load_sentiment_model(model_dir: str):
    return joblib.load(os.path.join(model_dir, "sentiment_model.joblib"))


def load_tfidf_vectorizer(model_dir: str):
    return joblib.load(os.path.join(model_dir, "tfidf_vectorizer.joblib"))


def load_sentiment_artifacts(model_dir: str):
    """Returns (sentiment_model, tfidf_vectorizer)."""
    return load_sentiment_model(model_dir), load_tfidf_vectorizer(model_dir)
