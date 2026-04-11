"""Standalone Top-Issues demo (no backend/frontend).

Run (from repo root):
    python3 backend/ml/testing/top_issues_standalone.py --csv path/to/reviews.csv

What it prints:
    1) (Best-effort) Sentiment model test accuracy if a training CSV exists
    2) Top Issues from negative reviews in the CSV

Notes:
- Default CSV path matches DS branch, but this repo may not ship the dataset.
- Implemented against the current runtime:
    - `app.services.ml_service.MLService` (v2 sentiment + NMF topic model artifacts)
    - `ml.core.issue_labeler.generate_issue_label()` (MiniLM taxonomy)
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

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

    try:
        from app.services.ml_service import MLService
        from ml.core.issue_labeler import generate_issue_label
        from ml.core.spam_filter import is_valid_review
        from ml.core.text_cleaner import clean_text
    except Exception as exc:
        print("Failed to import backend modules.")
        print(f"Details: {exc}")
        return 2

    svc = MLService()

    # -------- 1) Print sentiment accuracy (best-effort) --------
    if not args.skip_accuracy:
        metrics_csv = repo_root / "backend" / "data" / "training" / "processed" / "cleaned_all_combined.csv"
        if not metrics_csv.exists():
            print("Accuracy: skipped (training CSV not present)")
        else:
            try:
                from sklearn.metrics import accuracy_score
                from sklearn.model_selection import train_test_split
            except Exception:
                print("Accuracy: skipped (scikit-learn not installed)")
            else:
                df_metrics = pd.read_csv(metrics_csv)
                if "score" in df_metrics.columns and "cleaned_content" in df_metrics.columns:
                    y = df_metrics["score"].apply(lambda s: "negative" if float(s) <= 2 else "positive")
                    X = svc.vectorizer.transform(df_metrics["cleaned_content"].astype(str))
                    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                    y_pred = svc.sentiment_model.predict(X_test)
                    acc = float(accuracy_score(y_test, y_pred))
                    print(f"Accuracy: {acc:.4f} ({acc * 100:.2f}%)")
                else:
                    print("Accuracy: skipped (unexpected training CSV schema)")

    # -------- 2) Load reviews CSV --------
    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = repo_root / csv_path
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        print("Provide one via --csv.")
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
    filtered_reviews = raw_reviews if args.no_lang_filter else [r for r in raw_reviews if is_valid_review(r)]
    if not filtered_reviews:
        print("No valid reviews after filtering.")
        return 0

    print(f"Loaded rows: {len(df)}")
    print(f"After filter: {len(filtered_reviews)}")

    # -------- 3) Batch analyze + aggregate issues --------
    batch_size = 256
    issue_counts: Counter[str] = Counter()
    issue_examples: dict[str, list[str]] = defaultdict(list)
    negative_total = 0

    for start in range(0, len(filtered_reviews), batch_size):
        batch = filtered_reviews[start : start + batch_size]
        cleaned = [clean_text(t) for t in batch]

        X = svc.vectorizer.transform(cleaned)
        sentiments = svc.sentiment_model.predict(X).tolist()

        for text, sent in zip(cleaned, sentiments):
            if sent != "negative" or not text.strip():
                continue

            negative_total += 1
            topic_info = svc.predict_topic(text)
            label = generate_issue_label(topic_info["keywords"], encoder=svc.encoder)
            issue_counts[label] += 1

            if args.examples > 0 and len(issue_examples[label]) < args.examples:
                snippet = text.strip().replace("\n", " ")
                if len(snippet) > 180:
                    snippet = snippet[:177] + "..."
                issue_examples[label].append(snippet)

    if negative_total == 0:
        print("No negative reviews found in this sample.")
        return 0

    print(f"Negative reviews: {negative_total}")
    print("\nTop Issues (from negative reviews):")
    for rank, (label, count) in enumerate(issue_counts.most_common(args.top), start=1):
        pct = (count / negative_total) * 100
        print(f"{rank:>2}. {label} — {count} ({pct:.1f}%)")
        for ex in issue_examples.get(label, []):
            print(f"    - {ex}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
