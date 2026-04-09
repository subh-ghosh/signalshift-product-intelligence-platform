"""Standalone Top-Issues demo (no backend/frontend).

Run (from this folder):
    python top_issues_standalone.py

What it prints:
    1) Sentiment model test accuracy (80/20 split, random_state=42)
    2) Top Issues from negative reviews in the CSV

Notes:
- Requires artifacts in backend/models/: tfidf_vectorizer.joblib, sentiment_model.joblib
- Uses backend/data/testing/raw/netflix_reviews.csv by default
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Standalone Top Issues from reviews CSV")
    parser.add_argument(
        "--csv",
        default=os.path.join("backend", "data", "testing", "raw", "netflix_reviews.csv"),
        help="Path to reviews CSV (default: backend/data/testing/raw/netflix_reviews.csv)",
    )
    parser.add_argument(
        "--text-col",
        default="content",
        help="Text column name in the CSV (default: content)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=2000,
        help="Max rows to process (0 = all) (default: 2000)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="How many top issues to print (default: 10)",
    )
    parser.add_argument(
        "--examples",
        type=int,
        default=1,
        help="Example reviews to print per issue (default: 1)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.30,
        help="Minimum similarity confidence to assign a taxonomy label (default: 0.30)",
    )
    parser.add_argument(
        "--no-lang-filter",
        action="store_true",
        help="Skip is_valid_review() filtering (faster, less strict)",
    )

    parser.add_argument(
        "--skip-accuracy",
        action="store_true",
        help="Skip printing accuracy (faster)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    # -------- Resolve repo root + make backend importable --------
    here = Path(__file__).resolve()
    repo_root = None
    for parent in [here.parent, *here.parents]:
        if (parent / "backend" / "app").is_dir():
            repo_root = parent
            break
    if repo_root is None:
        print("Could not locate repo root (expected backend/app/).")
        return 2

    backend_path = str(repo_root / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    # -------- Imports (project modules) --------
    try:
        from app.services.paths import models_dir
        from app.services.sentiment_artifacts import load_sentiment_artifacts
        from app.services.taxonomy_embeddings import load_taxonomy_embeddings
        from ml.core.spam_filter import is_valid_review
        from ml.core.text_cleaner import clean_text
    except Exception as exc:
        print("Failed to import backend modules.")
        print(f"Details: {exc}")
        return 2

    # -------- Load trained artifacts --------
    model_dir = models_dir()
    try:
        sentiment_model, vectorizer = load_sentiment_artifacts(model_dir)
    except FileNotFoundError as exc:
        print("Missing trained model artifacts in backend/models/.")
        print("Expected files:")
        print("  - backend/models/tfidf_vectorizer.joblib")
        print("  - backend/models/sentiment_model.joblib")
        print(f"Details: {exc}")
        return 2

    # -------- 1) Print sentiment accuracy (one line) --------
    if not args.skip_accuracy:
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score

        metrics_csv = repo_root / "backend" / "data" / "training" / "processed" / "cleaned_all_combined.csv"
        df_metrics = pd.read_csv(metrics_csv)

        def rating_to_sentiment(score: float) -> str:
            return "negative" if score <= 2 else "positive"

        y = df_metrics["score"].apply(rating_to_sentiment)
        X = vectorizer.transform(df_metrics["cleaned_content"].astype(str))
        _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        y_pred = sentiment_model.predict(X_test)
        acc = float(accuracy_score(y_test, y_pred))
        print(f"Accuracy: {acc:.4f} ({acc * 100:.2f}%)")

    # -------- 2) Load reviews CSV --------
    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = repo_root / csv_path
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 2

    df = pd.read_csv(csv_path)
    if args.text_col not in df.columns:
        print(f"Text column '{args.text_col}' not found.")
        print("Available columns:", list(df.columns)[:25])
        return 2

    df = df.dropna(subset=[args.text_col]).copy()
    df[args.text_col] = df[args.text_col].astype(str)
    df = df[df[args.text_col].str.strip() != ""]
    if args.limit and args.limit > 0:
        df = df.head(args.limit).copy()
    df = df.reset_index(drop=True)

    raw_reviews = df[args.text_col].tolist()
    if args.no_lang_filter:
        filtered_reviews = raw_reviews
    else:
        filtered_reviews = [r for r in raw_reviews if is_valid_review(r)]

    if not filtered_reviews:
        print("No valid reviews after filtering.")
        return 0

    print(f"Loaded rows: {len(df)}")
    print(f"After filter: {len(filtered_reviews)}")

    # Sentiment prediction (batch)
    batch_size = 512
    sentiments: list[str] = []
    cleaned_reviews: list[str] = []

    for start in range(0, len(filtered_reviews), batch_size):
        batch = filtered_reviews[start : start + batch_size]
        cleaned = [clean_text(t) for t in batch]
        cleaned_reviews.extend(cleaned)

        X = vectorizer.transform(cleaned)
        pred = sentiment_model.predict(X)
        sentiments.extend(pred.tolist())

    neg_idx = [i for i, s in enumerate(sentiments) if s == "negative"]
    if not neg_idx:
        print("No negative reviews found in this sample.")
        return 0

    negative_texts = [cleaned_reviews[i] for i in neg_idx if cleaned_reviews[i].strip()]

    print(f"Negative reviews: {len(negative_texts)}")

    # Issue matching
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        print("Missing dependency: sentence-transformers")
        print("Install with: pip install -r backend/requirements.txt")
        print(f"Details: {exc}")
        return 2

    encoder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    try:
        taxonomy_labels, taxonomy_matrix = load_taxonomy_embeddings(model_dir, encoder=encoder)
    except FileNotFoundError:
        # topic_embeddings.pkl is optional; taxonomy_embeddings helper should normally fallback.
        # If it doesn't, provide a clear hint.
        print("Missing taxonomy embeddings artifact: backend/models/topic_embeddings.pkl")
        print("Run the pipeline step 04 to generate it, or check taxonomy embedding loader.")
        return 2

    # Ensure normalized taxonomy matrix (for dot-product = cosine similarity)
    taxonomy_matrix = np.array(taxonomy_matrix)
    if taxonomy_matrix.size:
        norms = np.linalg.norm(taxonomy_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        taxonomy_matrix = taxonomy_matrix / norms

    review_embeddings = encoder.encode(negative_texts, normalize_embeddings=True)

    issue_counts: Counter[str] = Counter()
    issue_examples: dict[str, list[str]] = defaultdict(list)

    for text, emb in zip(negative_texts, review_embeddings):
        sims = taxonomy_matrix.dot(emb)
        best_i = int(np.argmax(sims))
        best_score = float(sims[best_i])

        label = taxonomy_labels[best_i] if best_score >= args.min_confidence else "General App Feedback"

        issue_counts[label] += 1
        if args.examples > 0 and len(issue_examples[label]) < args.examples:
            # keep a short snippet
            snippet = text.strip().replace("\n", " ")
            if len(snippet) > 180:
                snippet = snippet[:177] + "..."
            issue_examples[label].append(snippet)

    print("\nTop Issues (from negative reviews):")
    for rank, (label, count) in enumerate(issue_counts.most_common(args.top), start=1):
        pct = (count / len(negative_texts)) * 100
        print(f"{rank:>2}. {label} — {count} ({pct:.1f}%)")
        for ex in issue_examples.get(label, []):
            print(f"    - {ex}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
